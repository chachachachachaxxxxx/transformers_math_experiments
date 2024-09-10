import subprocess
from slurm import init_signal_handler, init_distributed_mode
from utils import bool_flag, initialize_exp
import numpy as np
import time

from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Whitespace

import torch
import torch.nn as nn
from torch.nn import functional as F
from torch.utils.data import Dataset
from torch.utils.data.dataloader import DataLoader
from dataclasses import dataclass
from typing import List

from makemoretokens import ModelConfig, CharDataset, Transformer, Bigram, MLP, RNN, BoW, InfiniteDataLoader, evaluate, generate
import os
import argparse
os.environ["TOKENIZERS_PARALLELISM"] = "false"

def get_parser():
    parser = argparse.ArgumentParser('Generate training sample of low braids via reservoir sampling')
    # JULIA params
    parser.add_argument('--nb_local_searches', type=int, default=1200, help='N')
    parser.add_argument('--num_initial_empty_objects', type=int, default=500000, help='N')
    parser.add_argument('--final_database_size', type=int, default=50000, help='N')
    parser.add_argument('--target_db_size', type=int, default=500000, help='N')
    parser.add_argument('--sample-only', type=int, default=500000, help="sample the specified number from the model")
    

    # Makemore params
    parser.add_argument('--num-workers', '-n', type=int, default=8, help="number of data workers for both train/test")
    parser.add_argument('--max-steps', type=int, default=10000, help="max number of optimization steps to run for, or -1 for infinite.")
    parser.add_argument('--max_epochs', type=int, default= 1000, help='number of epochs')
    parser.add_argument('--seed', type=int, default=-1, help="seed")
    # sampling
    parser.add_argument('--top-k', type=int, default=-1, help="top-k for sampling, -1 means no top-k")
    # model
    parser.add_argument('--type', type=str, default='transformer', help="model class type to use, bigram|mlp|rnn|gru|bow|transformer")
    parser.add_argument('--n-layer', type=int, default=4, help="number of layers")
    parser.add_argument('--n-head', type=int, default=4, help="number of heads (in a transformer)")
    parser.add_argument('--n-embd', type=int, default=16, help="number of feature channels in the model")
    parser.add_argument('--n-embd2', type=int, default=16, help="number of feature channels elsewhere in the model")
    # optimization
    parser.add_argument('--batch-size', '-b', type=int, default=32, help="batch size during optimization")
    parser.add_argument('--learning-rate', '-l', type=float, default=5e-4, help="learning rate")
    parser.add_argument('--weight-decay', '-w', type=float, default=0.01, help="weight decay")
    # evaluation against known "good sequences"
    parser.add_argument('--max-output-length', type=int, default=100, help="maximum output length")
    

    # path and ports
    parser.add_argument("--dump_path", type=str, default="/checkpoint/fcharton/dumped",
                        help="Experiment dump path")
    parser.add_argument("--exp_name", type=str, default="debug",
                        help="Experiment name")
    parser.add_argument("--exp_id", type=str, default="",
                        help="Experiment ID")
    parser.add_argument("--local_rank", type=int, default=-1,
                        help="Multi-GPU - Local rank")
    parser.add_argument("--master_port", type=int, default=-1,
                        help="Master port (for multi-node SLURM jobs)")
    parser.add_argument("--cpu", type=bool_flag, default="false",
                        help="run on cpu only")
# debug
    parser.add_argument("--debug_slurm", type=bool_flag, default=False,
                        help="Debug multi-GPU / multi-node within a SLURM job")
    parser.add_argument("--debug", help="Enable all debug flags",
                        action="store_true")

    return parser



def tokenize(input_file_path, n_tokens):

    directory_name = args.dump_path + '/' + "tokenizer_data"
    tokenizer_file = directory_name + "/tokenizer.json"

    if os.path.exists(tokenizer_file):
        logger.info(f"Loading tokenizer from {tokenizer_file}...")
        tokenizer = Tokenizer.from_file(tokenizer_file)
    else:
        tokenizer = Tokenizer(BPE())
        tokenizer.pre_tokenizer = Whitespace()
    
        trainer = BpeTrainer(vocab_size=n_tokens)

        source_file_path = args.dump_path+'/search_output_1.txt'
        destination_file_path = args.dump_path+"/temp.txt"

        logger.info(f'Created {destination_file_path} and training tokenizer...')
        # Reading the first 100,000 lines from the source file and training the tokenizer on them
        with open(source_file_path, 'r') as source_file, open(destination_file_path, 'w') as destination_file:
            for i in range(100_000):
                line = source_file.readline()
                if not line:
                    break
                destination_file.write(line)

        if not os.path.isdir(directory_name):
            # Create the directory
            os.mkdir(directory_name)
            logger.info(f"Directory '{directory_name}' created.")

        tokenizer.train([destination_file_path], trainer)
        tokenizer.save(tokenizer_file)

        if os.path.exists(destination_file_path):
            os.remove(destination_file_path)
            logger.info(f"File '{destination_file_path}' has been deleted.")

    # input_file_path = input_path
    with open(input_file_path, "r") as file:
        text_data = [line.strip() for line in file]

    # Now create tokenized output file
    token_file_out = input_file_path.rsplit('.', 1)[0] + '-tokenized.txt'
    with open(token_file_out, "w") as file:
        print("Tokenizing training set...")
        for i, sequence in enumerate(text_data):
            if i % 10000 == 0:
                logger.info(f"{i} / {len(text_data)}")
            myids = tokenizer.encode(sequence).ids
            file.write(','.join(["V" + str(id) for id in myids]))
            file.write("\n")

def decode():
    # Load the tokenizer from the saved file
    tokenizer_path = os.path.join(args.dump_path+'/tokenizer_data', "tokenizer.json")
    if not os.path.exists(tokenizer_path):
        logger.error(f"No tokenizer found at {tokenizer_path}. Please check the path and try again.")

    tokenizer = Tokenizer.from_file(tokenizer_path)

    def decode_tokens(token_line):
        # Remove the 'V' prefix and convert to integers
        #print(token_line)
        token_ids = [int(token[1:]) for token in token_line.split(',')]
        # Decode the token ids to text
        
        return tokenizer.decode(token_ids).replace(" ","")


    # Process the input file
    input_file = args.dump_path+"/out.txt"
    if os.path.exists(input_file):
        with open(input_file, 'r') as file:
            tokenized_lines = file.readlines()

        # Decode each line and collect the results
        decoded_text = [decode_tokens(line.strip()) for line in tokenized_lines if len(line) > 1]

        # Write the decoded text to the output file
        output_file = args.dump_path+"/transformer-output-decoded.txt"
        with open(output_file, 'w') as file:
            for line in decoded_text:
                file.write(line + '\n')

        logger.info(f"Decoding complete. Check the output in {output_file}")
    else:
        logger.info(f"Error: The file {input_file} does not exist.")

def create_datasets(input_file):

    # preprocessing of the input text file
    with open(input_file, 'r') as f:
        data = f.read()
    words = data.splitlines()
    words = [w.strip() for w in words] # get rid of any leading or trailing white space
    words = [w for w in words if w] # get rid of any empty strings
    words = [w.split(",") for w in words]

    # maybe a tad hacky: we sort our dataset so that it is ordered V1, V2, .... V10, V11 ....
    chars = sorted(list(set([i for word in words for i in word])), key=lambda x: int(x[1:]))

    max_word_length = max(len(w) for w in words)
    logger.info(f"number of examples in the dataset: {len(words)}")
    logger.info(f"max word length: {max_word_length}")
    logger.info(f"number of unique characters in the vocabulary: {len(chars)}")
    logger.info("vocabulary:")
    logger.info(chars)
    assert max_word_length <= args.max_output_length, f'block size too large {max_word_length} vs {args.max_output_length}'
        
    # partition the input data into a training and the test set
    test_set_size = min(1000, int(len(words) * 0.1)) # 10% of the training set, or up to 1000 examples

    rp = torch.randperm(len(words)).tolist()
    train_words = [words[i] for i in rp[:-test_set_size]]
    test_words = [words[i] for i in rp[-test_set_size:]]
    logger.info(f"split up the dataset into {len(train_words)} training examples and {len(test_words)} test examples")
    
    # wrap in dataset objects
    train_dataset = CharDataset(train_words, chars, args.max_output_length)
    test_dataset = CharDataset(test_words, chars, args.max_output_length)

    return train_dataset, test_dataset

def write_samples(num=10, new_file=False, use_logger=False):
    """ samples from the model and pretty prints the decoded samples """
    X_init = torch.zeros(num, 1, dtype=torch.long).to(args.device)
    top_k = args.top_k if args.top_k != -1 else None
    steps = train_dataset.get_output_length() - 1 # -1 because we already start with <START> token (index 0)
    X_samp = generate(model, X_init, steps, top_k=top_k, do_sample=True).to('cpu')
    samples = []
#    train_samples, test_samples, new_samples = [], [], []
    for i in range(X_samp.size(0)):
        # get the i'th row of sampled integers, as python list
        row = X_samp[i, 1:].tolist() # note: we need to crop out the first <START> token
        # token 0 is the <STOP> token, so we crop the output sequence at that point
        crop_index = row.index(0) if 0 in row else len(row)
        row = row[:crop_index]
        word_samp = train_dataset.decode(row)
        samples.append(word_samp)
    out_file = args.dump_path + "/out.txt"
    if use_logger:
        logger.info(f"Printing {len(samples)} samples to {out_file}.")
    else: 
        print(f"Printing {len(samples)} samples to {out_file}.")
    if not new_file:
        with open(out_file, "a") as file:
            for word in samples:
                file.write(word)
                file.write("\n")
    else:
        with open(out_file, "w") as file:
            for word in samples:
                file.write(word)
                file.write("\n")


if __name__ == '__main__':
    parser = get_parser()
    args = parser.parse_args()
    init_distributed_mode(args)
    logger = initialize_exp(args)
    if args.is_slurm_job:
        init_signal_handler()
    
    args.device = "cpu" if args.cpu else "cuda"
    if args.seed < 0:
        args.seed = np.random.randint(1_000_000_000)
    logger.info(f"seed: {args.seed}")

    # system inits
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    # os.makedirs(args.work_dir, exist_ok=True)

    # init datasets
    for i in range(1,args.max_epochs):
        if not os.path.isfile(f"{args.dump_path}/search_output_{i}-tokenized.txt"):
            break
    initial_gen = i-1
    if initial_gen == 0:
        subprocess.run(["julia","search_fc.jl", args.dump_path, str(args.nb_local_searches), str(args.num_initial_empty_objects), str(args.final_database_size), str(args.target_db_size)])
        tokenize(f"{args.dump_path}/search_output_1.txt", 100)
        initial_gen = 1
    
    logger.info(f"initializing at generation: {initial_gen}")
    input_file = args.dump_path + f"/search_output_{initial_gen}-tokenized.txt"
    train_dataset, test_dataset = create_datasets(input_file)
    vocab_size = train_dataset.get_vocab_size()
    block_size = args.max_output_length + 1
    logger.info(f"dataset determined that: {vocab_size=}, {block_size=}")

    # init model
    config = ModelConfig(vocab_size=vocab_size, block_size=block_size,
                       n_layer=args.n_layer, n_head=args.n_head,
                       n_embd=args.n_embd, n_embd2=args.n_embd2)
    if args.type == 'transformer':
        model = Transformer(config)
    elif args.type == 'bigram':
        model = Bigram(config)
    elif args.type == 'mlp':
        model = MLP(config)
    elif args.type == 'rnn':
        model = RNN(config, cell_type='rnn')
    elif args.type == 'gru':
        model = RNN(config, cell_type='gru')
    elif args.type == 'bow':
        model = BoW(config)
    else:
        logger.error(f'model type {args.type} is not recognized')
    model.to(args.device)
    logger.info(f"model #params: {sum(p.numel() for p in model.parameters())}")
    model_path = os.path.join(args.dump_path, "model.pt")
    if os.path.isfile(model_path): # Note: if we sample-only then we also assume we are resuming
        logger.info("resuming from existing model")
        model.load_state_dict(torch.load(model_path))


    for generation in range(initial_gen,args.max_epochs + 1):
        logger.info(f"============ Start of generation {generation} ============")
        
        logger.info("training")
        # python makemoretokens.py --i search_output_1-tokenized.txt --device cuda
        #train_makemore()
        # init optimizer
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay, betas=(0.9, 0.99), eps=1e-8)

        # init dataloader
        batch_loader = InfiniteDataLoader(train_dataset, batch_size=args.batch_size, pin_memory=True, num_workers=args.num_workers)

        # training loop
        best_loss = None
        step = 0
        while True:

            t0 = time.time()

            # get the next batch, ship to device, and unpack it to input and target
            batch = batch_loader.next()
            batch = [t.to(args.device) for t in batch]
            X, Y = batch

            # feed into the model
            logits, loss = model(X, Y)

            # calculate the gradient, update the weights
            model.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

            # wait for all CUDA work on the GPU to finish then calculate iteration time taken
            if args.device =="cuda":
                torch.cuda.synchronize()
            t1 = time.time()

            # logging
            if step % 10 == 0:
                logger.info(f"step {step} | loss {loss.item():.4f} | step time {(t1-t0)*1000:.2f}ms")

            # evaluate the model
            if step > 0 and step % 500 == 0:
                train_loss = evaluate(model, train_dataset, args.device, batch_size=100, max_batches=10)
                test_loss  = evaluate(model, test_dataset,  args.device, batch_size=100, max_batches=10)
                logger.info(f"step {step} train loss: {train_loss} test loss: {test_loss}")
                # save the model to disk if it has improved
                if best_loss is None or test_loss < best_loss:
                    out_path = os.path.join(args.dump_path, "model.pt")
                    logger.info(f"test loss {test_loss} is the best so far, saving model to {out_path}")
                    torch.save(model.state_dict(), out_path)
                    best_loss = test_loss
    #            print_samples(num=10)
                    
            step += 1
            # termination conditions
            if args.max_steps >= 0 and step >= args.max_steps:
                break

        logger.info('generating')
        sample_batch_size = 1000 # reduce this if GPU crashes, increase it if sampling is slow
        todo = args.sample_only
        write_samples(num=0, new_file=True)
        while sample_batch_size < todo:
            logger.info(f'{todo} samples remaining', end="\r")
            write_samples(num=sample_batch_size)
            todo = todo - sample_batch_size
        write_samples(num=todo)

        logger.info('decoding')
        decode()
        logger.info(f"============ End of generation {generation} ============")
        logger.info(f"launching search.jl")
        subprocess.run(["julia","search_fc.jl", args.dump_path, str(args.nb_local_searches), str(args.num_initial_empty_objects), str(args.final_database_size), str(args.target_db_size),'-i',args.dump_path+'/transformer-output-decoded.txt'])
        logger.info("tokenizing")
        tokenize(f"{args.dump_path}/search_output_{generation+1}.txt", 100)
        input_file = args.dump_path + f"/search_output_{generation+1}-tokenized.txt"
        train_dataset, test_dataset = create_datasets(input_file)
        
