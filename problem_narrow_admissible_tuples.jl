include("constants.jl")

const K = 8
const MAX_FIRST_NUMBER = 20
const MAX_DIFF_BETWEEN_NUMBERS = 10
const PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


function greedy_search_from_startpoint(db, obj::OBJ_TYPE)::OBJ_TYPE
    """
    Main greedy search algorithm. 
    It starts and ends with some construction 
    
    E.g. input: a graph which may or may not have triangles in it (these are the outputs of the transformer)
    Greedily remove edges to destroy all triangles, then greedily add edges without creating triangles
    Returns final maximal triangle-free graph
    """

    # If we don't have a greedy search algorithm we can just return the sequence without modifying it
    # This way the transformer has to do all the work. I am not sure how well this would work,
    # but it's an interesting experiment nevertheless!
    return obj 
end

function reward_calc(obj::OBJ_TYPE)::REWARD_TYPE
    """
    Function to calculate the reward of a final construction
    (E.g. number of edges in a graph, etc)
    """

    parts = split(obj, ",")
    diffs = [parse(Int, part) for part in parts]

    # Now the 'diffs' array contains all the m_i-s from your email. 
    # We can recover the tuple from this easily.
    
    # The first number in our code actually represents the first number
    numbers = [diffs[1]]

    # All further numbers in the code represent numbers[i] - numbers[i-1]
    for i in 2:K 
        push!(numbers, numbers[i-1] + diffs[i])
    end

    # Now the 'numbers' array contains the K-tuple.
    # All that's left is to calculate its reward.

    penalty = 0

    # We count for how many primes do we see all possible residues

    for prime in PRIMES
        if length(Set([number % prime for number in numbers])) == prime
            penalty += 1 
        end
        if prime > K
            break
        end
    end

    # The goal is to have penalty == 0, then the tuple is admissible.
    # We want to minimize the width of the tuple

    width = numbers[K] - numbers[1]

    # I guess a good reward function is -width (so that we minimize the width), minus C * penalty?

    return -width - 100 * penalty 
end


function empty_starting_point()::OBJ_TYPE
    """
    If there is no input file, the search starts with a random string
    """
    random_string = string(rand(1:MAX_FIRST_NUMBER))
    
    for i in 2:K
        part = rand(1:MAX_DIFF_BETWEEN_NUMBERS)
        random_string *= ",$part"
    end
    
    return random_string
end