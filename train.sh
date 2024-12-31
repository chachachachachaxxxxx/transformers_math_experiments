python fc_loop.py --type bigram --exp_name "bigramK3free"

python fc_loop.py --exp_name "transformerK3free" --max_epochs 20 --type transformer --n-layer 2 --n-head 4 --n-embd 16 

python fc_loop.py --exp_name "RotaryTransformerK3free" --max_epochs 20 --type RotaryTransformer --n-layer 2 --n-head 4 --n-embd 16 

python fc_loop.py --exp_name "transformerC4free" --max_epochs 40 --type transformer --n-layer 4 --n-head 4 --n-embd 128 

python fc_loop.py --exp_name "RotarytransformerC4free" --max_epochs 40 --type RotaryTransformer --n-layer 4 --n-head 4 --n-embd 128 