const N::Int = 12                     # Some natural parameter of the problem, e.g. number of vertices
const NB_LOCAL_SEARCHES::Int64 = 1200 # number of local searches to do at once. 
                                      # probably best to set it divisible by number of threads, if using multithreading
                                      # increase this number if episodes are too fast

const NUM_INITIAL_EMPTY_OBJECTS = 200_000 #on the first run, this many rollouts will be done from empty graphs/objects
const FINAL_DATABASE_SIZE = 20_000

const OBJ_TYPE = String  # type for vectors encoding constructions
const REWARD_TYPE = Float32  # type for rewards 