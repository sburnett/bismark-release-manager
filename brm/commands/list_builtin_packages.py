import glob
import os

def run(args):
    filename = os.path.join(args.root, args.release, 'builtin-packages')
    with open(filename) as handle:
        for line in handle:
            words = line.split()
            if len(words) != 3:
                return 'malformed built-packages file: incorrect number of columns'
            architecture = words[2]
            if architecture != args.architecture and architecture != 'all':
                continue
            print words[0], words[1]
