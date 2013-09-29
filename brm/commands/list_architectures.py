import glob
import os

def run(args):
    filename = os.path.join(args.root, args.release, 'architectures')
    with open(filename) as handle:
        for line in handle:
            print line.strip()
