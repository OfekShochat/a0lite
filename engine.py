import search
import chess
import chess.pgn
import sys
import traceback

CACHE_SIZE = 200000
MINTIME = 0.1
TIMEDIV = 20.0
NODES = 800
C = 2.2


logfile = open("a0lite.log", "a+")
LOG = True

def log(msg):
    if LOG:
        logfile.write(str(msg))
        logfile.write("\n")
        logfile.flush()

def send(str):
    log(">{}".format(str))
    sys.stdout.write(str)
    sys.stdout.write("\n")
    sys.stdout.flush()

def process_position(tokens):
    board = chess.Board()

    offset = 0

    if tokens[1] ==  'startpos':
        offset = 2
    elif tokens[1] == 'fen':
        fen = " ".join(tokens[2:8])
        board = chess.Board(fen=fen)
        offset = 8

    if offset >= len(tokens):
        return board

    if tokens[offset] == 'moves':
        for i in range(offset+1, len(tokens)):
            board.push_uci(tokens[i])

    return board





def load_network():
    log("Loading network")

    #net = search.EPDLRUNet(search.BadGyalNet(cuda=True), CACHE_SIZE)
    net = search.EPDLRUNet(search.BadGyalTorchNet(cuda=True), CACHE_SIZE)
    #net = search.EPDLRUNet(search.MeanGirlNet(cuda=False), CACHE_SIZE)
    #net = search.BadGyalNet(cuda=True)
    return net


def main():

    send("A0 Lite")
    board = chess.Board()
    nn = None
    # get ready for tree reuse
    tree = None

    while True:
        line = sys.stdin.readline()
        line = line.rstrip()
        log("<{}".format(line))
        tokens = line.split()
        if len(tokens) == 0:
            continue

        if tokens[0] == "uci":
            send('id name A0 Lite')
            send('id author Dietrich Kappe')
            send('uciok')
        elif tokens[0] == "quit":
            exit(0)
        elif tokens[0] == "isready":
            if nn == None:
                nn = load_network()
            send("readyok")
        elif tokens[0] == "ucinewgame":
            board = chess.Board()
            tree = None
        elif tokens[0] == 'position':
            board = process_position(tokens)
            # see if we can reuse the three
            if tree != None:
                tree = tree.childByEpd(board.epd())
                if tree != None:
                    tree.makeroot()
        elif tokens[0] == 'go':
            if board.is_game_over(claim_draw=False):
                send("bestmove (none)")
                continue
            my_nodes = NODES
            my_time = None
            if (len(tokens) == 3) and (tokens[1] == 'nodes'):
                my_nodes = int(tokens[2])
            if (len(tokens) == 3) and (tokens[1] == 'movetime'):
                my_time = int(tokens[2])/1000.0
                if my_time < MINTIME:
                    my_time = MINTIME
            if (len(tokens) == 9) and (tokens[1] == 'wtime'):
                wtime = int(tokens[2])
                btime = int(tokens[4])
                winc = int(tokens[6])
                binc = int(tokens[8])
                if (wtime > 5*winc):
                    wtime += 5*winc
                else:
                    wtime += winc
                if (btime > 5*binc):
                    btime += 5*binc
                else:
                    btime += binc
                if board.turn:
                    my_time = wtime/(TIMEDIV*1000.0)
                else:
                    my_time = btime/(TIMEDIV*1000.0)
                if my_time < MINTIME:
                    my_time = MINTIME
            if nn == None:
                nn = load_network()

            if tree != None and not tree.match_position(board):
                tree = None

            if tree != None:
                sz, exp_sz = tree.size()
                send("info string tree size {}, expanded {}".format(sz, exp_sz))
            else:
                send("info string no tree reuse")
            if my_time != None:
                best, score, tree = search.UCT_search(board, 1000000, net=nn, C=C, max_time=my_time, send=send, tree=tree)
            else:
                best, score, tree = search.UCT_search(board, my_nodes, net=nn, C=C, send=send, tree=tree)
            send("bestmove {}".format(best))

try:
    main()
except:
    exc_type, exc_value, exc_tb = sys.exc_info()
    log(traceback.format_exception(exc_type, exc_value, exc_tb))

logfile.close()
