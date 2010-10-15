#!/usr/bin/env python
"""A mapper for hadoop task parallelism. 

To test the mapper locally use:
> cat tasks.txt| ./mapper.py


To send to Hadoop use:
hadoop jar /usr/lib/hadoop/contrib/streaming/hadoop-0.18.3-2cloudera0.3.0-streaming.jar \
    -input tmptasks.txt \
    -output tmpout \
    -mapper dumbo.py \
    -file dumbo.py \
    -file examples.npy \
    -jobconf mapred.reduce.tasks=0 \
    -jobconf mapred.input.format.class=org.apache.hadoop.mapred.lib.NLineInputFormat \
    -jobconf mapred.line.input.format.linespermap=1


"""
 
import sys
import copy
import math
import numpy as np

try:
    import json
except ImportError:
    import simplejson as json

try:
    import cPickle as pickle
except:
    import pickle

import bolt

import util

T = 10**6

def serialize(arr):
    return " ".join(["%d:%.20f"%(idx,arr[idx]) for idx in arr.nonzero()[0]])

def train(ds, reg = 0.00001, alpha = 0.85, norm = 2):
    epochs = int(math.ceil(float(T) / float(ds.n)))
    loss = bolt.ModifiedHuber()
    model = bolt.LinearModel(ds.dim, biasterm = False)
    sgd = bolt.SGD(loss, reg, epochs = epochs, norm = norm, alpha = alpha)
    sgd.train(model, ds, verbose = 0, shuffle = False)
    return model.w

  
def main(separator='\t'):
    # input comes from STDIN (standard input)

    ds = bolt.io.MemoryDataset.load("examples.npy", verbose = 0)
    
    for line in sys.stdin.xreadlines():
	line = line.rstrip()
	rid = "rid"+str(hash(line)) # run id
	line = line.split("\t")[-1]
	params = json.loads(line)
	taskid = params[u"taskid"]
	auxtask = params[u"task"]
	reg = params[u"reg"]
	alpha = params.get(u"alpha",0.15)
	norm = params.get(u"norm",3)
	
	instances = copy.deepcopy(ds.instances)
	labels = util.autolabel(instances, auxtask)
	util.mask(instances, auxtask)
	maskedds = bolt.io.MemoryDataset(ds.dim, instances, labels)
	w = train(maskedds, reg = reg, alpha = alpha, norm = norm)
	if norm == 2:
	    w[w<0.0] = 0.0
        sw = serialize(w)  
	print >> sys.stdout, "%d\t%s" % (taskid,sw)

if __name__ == "__main__":
    main()