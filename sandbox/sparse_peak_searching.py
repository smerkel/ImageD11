
from __future__ import print_function, division

import time, sys
import h5py, scipy.sparse, numpy as np, pylab as pl
from ImageD11 import cImageD11

# see also sandbox/collect_peak_pixels.py

class sparse_frame( object ):
    """
    Holds the output of an image segmentation
    """
    def __init__(self, row, col, pixels, shape=None, name="none"):
        """
        Sparse matrix, follows scipy.sparse.coo_matrix
        row = slow index (uint16)
        col = fast index (uint16)
        data = intensity
        nnz  = number of entries
        """
        self.row = np.array(row, dtype=np.uint16)
        self.col = np.array(col, dtype=np.uint16)
        self.pixels = pixels
        self.nnz = len(self.row)
        self.cplabels=None # flags for done/not done
        self.mxlabels=None
        self.name=name
        if shape is None:
            self.shape = (self.row.max(), self.col.max())
        else:
            self.shape = shape
            assert self.row.max() <= self.shape[0]
            assert self.col.max() <= self.shape[1]
                
    def check(self):
        """
        Verify data type and that indices are sorted
        """
        assert self.row.dtype == np.uint16
        assert self.col.dtype == np.uint16
        assert cImageD11.sparse_is_sorted( self.row, self.col ) == 0
        for ar in (self.row, self.col, self.pixels):
            assert len(ar.shape)==1
            assert ar.shape[0] == self.nnz

    def threshold(self, threshold):
        m = self.pixels > t
        return sparse_frame( self.row[m], self.col[m], self.pixels[m] )

    def con_labels( self, threshold=None ):
        if threshold is None:
            self.threshold = self.pixels.min()-1
        self.cplabels = np.zeros( self.nnz, 'i' )
        self.nclabel = cImageD11.sparse_connectedpixels(
            self.pixels, self.row, self.col,
            self.threshold,   self.cplabels )
        
    def con_moments( self ):
        if self.cplabels is None:
            self.con_labels()
        return cImageD11.sparse_blob2Dproperties(
            self.pixels, self.row, self.col, self.cplabels, self.nclabel )

    def max_labels( self ):
        self.mxlabels = np.zeros(self.nnz, 'i' )
        vmx = np.zeros( self.nnz, np.float32 )
        imx = np.zeros( self.nnz, 'i')
        self.nmlabel = cImageD11.sparse_localmaxlabel(
            self.pixels, self.row, self.col,
            vmx, imx,   self.mxlabels )
        
    def max_moments( self ):
        if self.mxlabels is  None:
            self.max_labels()
        return cImageD11.sparse_blob2Dproperties(
            self.pixels, self.row, self.col,
            self.mxlabels, self.nmlabel )
        
    def overlaps(self, other, labels="max"):
        """
        figures out which label of self matches which label of other
        Returns sparse array of:
           label in self (row)
           label in other (col)
           number of shared pixels (data)
        """
        ki = np.empty(  self.nnz, 'i' )
        kj = np.empty( other.nnz, 'i' )
        npx = cImageD11.sparse_overlaps( self.row, self.col, ki,
                                         other.row, other.col, kj)
        # self.data and other.data filled during init
        row = self.mxlabels[ ki[:npx] ]  # my labels
        col = other.mxlabels[ kj[:npx] ] # your labels
        ect = np.empty( npx, 'i')    # ect = counts of overlaps
        tj  = np.empty( npx, 'i')    # tj = temporary  for sorting
        tmp = np.empty( max(self.nmlabel, other.nmlabel)+1, 'i') # for histogram
        
        nedge = cImageD11.compress_duplicates( row, col, ect, tj, tmp )
        # overwrites row/col in place
        crow = row[:nedge]
        ccol = col[:nedge]
        cdata = ect[:nedge]
        cedges = scipy.sparse.coo_matrix( ( cdata, (crow, ccol)) )
        return cedges

    def tohdf( self, hdffile ):
        opts = { 'compression':'gzip', 'compression_opts':4 }
        g = hdffile.require_group( self.name )
        g.attrs['sigma_cut']=self.sigma_cut
        g.attrs['nnz']      = self.nnz
        g.attrs['nmlabel']  = self.nmlabel
        g.attrs['nclabel']  = self.nclabel
        g.attrs['shape0']   = self.shape[0]
        g.attrs['shape1']   = self.shape[1]
        g.require_dataset( 'row', (self.nnz,), dtype=np.uint16,
                           chunks = (self.nnz,),
                           data=self.row, **opts )
        g.require_dataset( 'col', (self.nnz,), dtype=np.uint16,
                           chunks = (self.nnz,),
                           data=self.col, **opts )
        g.require_dataset( 'pixels', (self.nnz,), dtype=np.float32,
                           chunks = (self.nnz,),
                           data=self.pixels, **opts )
        g.require_dataset( 'mxlabels', (self.nnz,), dtype=np.int32,
                           chunks = (self.nnz,),
                           data=self.mxlabels, **opts )
        g.require_dataset( 'cplabels', (self.nnz,), dtype=np.int32,
                           chunks = (self.nnz,),
                           data=self.cplabels, **opts )

def sparse_frame_from_hdfo( g, name ):
    row = g['row']
    col = g['col']
    pixels = g['pixels']
    shape  = g.attrs['shape0'], g.attrs['shape1']
    spar = sparse_frame( row, col, pixels, shape=shape, name=name)
    return spar
        
def sparse_frames_from_hdf( hdfname ):
    raise TODONEXT
    h = h5py.File( hdfname, "r" )
    g = h[list(h)[0]]
    frames = [sparse_frame_from_hdfo( g[name], name ) for name in list(g)]
    return frames

def dosave(frames, attr, grp, npx):
    dt = getattr(frames[0], attr).dtype
    d = grp.require_dataset( attr, (npx,), dtype=dt,
                             compression= 'gzip',
                             compression_opts=4)
    s=0
    for f in frames:
        d[s:s+f.nnz] = getattr( f, attr )
        s+=f.nnz
        

def sparse_frames_to_hdf( hdfname, hdfgrp, frames ):
    """
    pack a long list of frames to a single file
    """
    h = h5py.File(hdfname)
    g = h.require_group( hdfgrp )
    # full image shape
    g.attrs['shape0'] = frames[0].shape[0]
    g.attrs['shape1'] = frames[0].shape[1]
    # number of non zeros per image [needed to unpack]
    nnz = np.array( [f.nnz for f in frames], np.int32 )
    g.require_dataset( 'nnz', (len(frames),), np.int32, data=nnz )
    # threshold used for making cut
    sc = np.array( [f.sigma_cut for f in frames], np.float32 )
    g.require_dataset( 'sigma_cut', (len(frames),), np.float32, data=sc )
    # array data : i,j,intensity [appended for all frames]
    npx = np.sum(nnz)
    dosave( frames, "row", g, npx )
    dosave( frames, "col", g, npx )
    dosave( frames, "pixels", g, npx )
    # connected pixels labelling
    nc = np.array( [f.nclabel for f in frames], np.int32 )
    g.require_dataset( 'nclabel', (len(frames),), np.int32, data=nc )
    dosave( frames, "cplabels", g, npx )
    # localmax labelling
    nm = np.array( [f.nmlabel for f in frames], np.int32 )
    g.require_dataset( 'nmlabel', (len(frames),), np.int32, data=nm )
    dosave( frames, "mxlabels", g, npx )


    
    

timer = time.time
def toc(msg):
    global tic
    now = timer()
    print(msg, "%.3f s"%( now - tic))
    tic = now

def read_csr_from_hdf( fname, pname ):
        """
        Reads a sparse matrix from a hdf file(fname)/group(pname)
        """
        h = h5py.File( fname, "r" )
        try:
            p = h[pname]
        except:
            print(list(h))
            raise
        shape = p.attrs['h5sparse_shape']
        assert p.attrs['h5sparse_format'] == 'csr'
        vals = p['data'][:]
        indices = p['indices'][:]
        indptr = p['indptr'][:]
        obj = scipy.sparse.csr_matrix( ( vals, indices, indptr ), shape=shape )
        return obj


def readhdfframes( stem ):
    a40 = read_csr_from_hdf(stem+".hdf", stem)
    # ouch:
    frames = []
    for i in range(0,a40.shape[0]//1024):
        tmp  =  a40[i*1024:(i+1)*1024].tocoo()
        frame = sparse_frame( tmp.row, tmp.col, tmp.data )
        frame.check()
        frames.append( frame )
    return frames

tic = timer()
def main():    

    frames_a40 = readhdfframes( "Au6_s0_040_a" )
    toc("to coo")
    #cl = [ cplabels(f) for f in frames ]
    #toc("assign and count t==0")
    ml = [ f.max_labels() for f in frames_a40 ]
    toc("maxlabel")
    # Next step : pair up the max labels with connectedpixels labels?
    #   con_pk_list : shorter list
    #   max_pk_list : longer list
    #
    # cases :     1 <-> 1 = same
    #             1  -> n : split them or not ?
    #                   shared boundaries / perimeter / other ?
    #
    # Parent child relation in this specific case. Localmax is always
    # a connected object so that each maxlabel has one parent connected
    #
    # >>> maxlabels[0]
    # array([  1,   1,   2, ..., 668, 668, 668], dtype=int32)
    # >>> labels[0]
    # array([  1,   1,   2, ..., 347, 347, 347], dtype=int32)
    #
    # Cases:
    #    noisy satellites :
    #         identify as s_I(child) or s_1(child) << s_I(parent)
    #                     many pixels on the border or close to threshold
    #    split peaks:
    #         tails are touching : I_shared << I_max[i,j]
    #         peaks are overlapping : I_shared ~ I_max * frac
    # Classify pixels into:
    #    fully inside child (8 neighbors with equal label)
    #       9 labels     0, 1, 2,
    #                    3, 4, 5,
    #                    6, 7, 8
    #    can be 0 = border        
    #        -> k == neighbor link
    #    labels[4] -> labels[j] score v[4] ... when we see j->4 we count v[j]
    #    eventually count 8X intensity in links
    #
    # Graphing :
    #   max-labels are nodes in the graph (image_id, node_id)
    #     links are then pairs of these.
    #
    #edges = []
    #for i in range(len(cl)):
    #    edges.append( cl[i].overlaps( ml[i] ) )
    #toc("cp mx pairs")
    #cpedges=[]
    #for i in range(1, len(cl)):
    #    cpedges.append( cl[i].overlaps( cl[i-1] ) )
    #toc("cp cp[-1] pairs")
    mxedges=[]
    for i in range(1, len(frames_a40)):
        mxedges.append( frames_a40[i].overlaps( frames_a40[i-1] ) )
    toc("mx mx[-1] pairs")
    #    allpairs.append(
    #        pairs(frames_a40[i-1], maxlabels[i-1], frames_a40[i], maxlabels[i] )) 
        
    # foreach frame :
    #     row/col/intensity/labels
    # foreach pixel frame_i and frame_j
    #     overlaps : assign intensity to i,li,j,lj bucket
    #     in one only : assign intensity to i,li   bucket
    if 0:
        pl.plot( npx, "o-")
        pl.show()

if __name__=="__main__":
    main()
            
