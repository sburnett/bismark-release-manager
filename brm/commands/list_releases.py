import glob
import os

def run(args):
    pattern = os.path.join(args.root, '*')
    for filename in glob.iglob(pattern):
        if not os.path.isdir(filename):
            continue
        print os.path.basename(filename)
