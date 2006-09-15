

# ImageD11_v0.4 Software for beamline ID11
# Copyright (C) 2005  Jon Wright
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


from Numeric import *
#from Imaged11Functions import closest


import math,time,sys
def ubitocellpars(ubi):
    """
    convert ubi matrix to unit cell
    """
    g=matrixmultiply(ubi,transpose(ubi))
    a=sqrt(g[0,0])
    b=sqrt(g[1,1])
    c=sqrt(g[2,2])
    from math import acos, degrees
    alpha=degrees(acos(g[1,2]/b/c))
    beta =degrees(acos(g[0,2]/a/c))
    gamma=degrees(acos(g[0,1]/a/b))
    return a,b,c,alpha,beta,gamma

def mod_360(theta, target):
    """
    Find multiple of 360 to add to theta to be closest to target
    """
    diff=theta-target
    while diff < -180:
        theta=theta+360
        diff=theta-target
    while diff > 180:
        theta=theta-360
        diff=theta-target
    return theta

def refine(UBI,gv,tol,quiet=True):
    """
    Refine an orientation matrix and rescore it.

    From Paciorek et al Acta A55 543 (1999)
       UB = R H-1
    where:
       R = sum_n r_n h_n^t
       H = sum_n h_n h_n^t
       r = g-vectors
       h = hkl indices
    """
    #      print "Orientation and unit cell refinement of"
    #      print "UBI\n",UBI
    #      print "Scores before",self.score(UBI)
    # Need to find hkl indices for all of the peaks which are indexed
    h=matrixmultiply(UBI,transpose(gv))
    hint=floor(h+0.5).astype(Int) # rounds down
    diff=h-hint
    drlv2=sum(diff*diff,0)
    tol = float(tol)
    tol = tol*tol
    # Only use peaks which are assigned to rings for refinement
    ind = compress( less(drlv2,tol) , arange(gv.shape[0]) )
    scoreb4=ind.shape[0]
    contribs = take(drlv2,ind)
    try:
        fitb4=math.sqrt(sum(contribs)/contribs.shape[0])
        if not quiet:
            print "Fit before refinement %.8f %5d"%(fitb4,contribs.shape[0]),
    except:
        print "No contributing reflections for\n",UBI
        raise
    drlv2_old=drlv2
    R=zeros((3,3),Float)
    H=zeros((3,3),Float)
    for i in ind:
        r = gv[i,:]
        k = hint[:,i].astype(Float)
        #           print r,k
        R = R + outerproduct(r,k)
        H = H + outerproduct(k,k)
    from LinearAlgebra import inverse
    try:
        HI=inverse(H)
        UBoptimal=matrixmultiply(R,HI)
        UBIo=inverse(UBoptimal)
    except:
        # A singular matrix - this sucks.
        UBIo=UBI
    h=matrixmultiply(UBIo,transpose(gv))
    hint=floor(h+0.5).astype(Int) # rounds down
    diff=h-hint
    drlv2=sum(diff*diff,0)
    ind = compress( less(drlv2,tol), arange(gv.shape[0]) )
    scorelastrefined=ind.shape[0]
    contribs = take(drlv2,ind)
    try:
        fitlastrefined=math.sqrt(sum(contribs)/contribs.shape[0])
        if not quiet:
            print "after %.8f %5d"%(fitlastrefined,contribs.shape[0])
    except:
        print "\n\n\n"
        print "No contributing reflections for\n",UBI
        print "After refinement, it was OK before ???"
        print "\n\n\n"
        return UBI
        raise
    #      for i in ind:
    #         print "( %-6.4f %-6.4f %-6.4f ) %12.8f %12.8f"%(h[0,i],h[1,i],h[2,i],sqrt(drlv2[i]),sqrt(drlv2_old[i]))
    #      print UBIo
    #      print "Scores after", self.score(UBIo,self.hkl_tol)
    #      print "diff\n",UBI-UBIo
    #      print "Mean drlv now",sum(sqrt(drlv2))/drlv2.shape[0],
    #      print "Mean drlv old",sum(sqrt(drlv2_old))/drlv2_old.shape[0]
    return UBIo




class indexer:
    """
    A class for searching for orientation matrices
    """
    def __init__(self,unitcell=None,gv=None,
          cosine_tol = 0.002,
          minpks = 10 ,
          hkl_tol=0.01,
          ring_1=1,
          ring_2=2,
          ds_tol=0.005,
          wavelength=-1,
          uniqueness=0.5,
          eta_range=0.,
          max_grains=100):
        """
        Unitcell would be a unitcell object for generating hkls peaks
        gv would be a 3*n array of points in reciprocal space
        """
        self.unitcell=unitcell
        self.gv=gv
        self.wedge=0.0 # Default
        if gv !=None:
            self.gvflat=reshape(fromstring(self.gv.tostring(),Float),self.gv.shape) # Makes it contiguous in memory, hkl fast index

        self.cosine_tol=cosine_tol
        self.wavelength=wavelength
        self.hkl_tol=hkl_tol
        self.ring_1=ring_1
        self.ring_2=ring_2
        self.uniqueness=uniqueness
        self.minpks=minpks
        self.ds_tol=ds_tol
        self.max_grains=max_grains
        self.eta_range = eta_range
        self.ubis=[]
        self.scores=[]


        # it would make more sense to inherit the parameter object - will
        # have to think about this some more - how general is it?
        from ImageD11 import parameters
        self.parameterobj = parameters.parameters(cosine_tol=self.cosine_tol,
              hkl_tol=self.hkl_tol, ring_1=self.ring_1, ring_2=self.ring_2,
              minpks=self.minpks, uniqueness=self.uniqueness, ds_tol=self.ds_tol,
              wavelength=self.wavelength, eta_range=self.eta_range)
        
        import plot3d
        self.plot3d=None

    def updatepars(self, cosine_tol, ds_tol, eta_range, hkl_tol, minpks, ring_1,
                    ring_2, uniqueness, wavelength, max_grains):
        """
        Updates values of parameters, temporary used for 
        XML-RPC communication 
        """
        self.cosine_tol=cosine_tol
        self.wavelength=wavelength
        self.hkl_tol=hkl_tol
        self.ring_1=ring_1
        self.ring_2=ring_2
        self.uniqueness=uniqueness
        self.minpks=minpks
        self.ds_tol=ds_tol
        self.max_grains=max_grains
        self.eta_range = eta_range
        return "OK"

    def loadpars(self,filename=None):
        if filename is not None:
            self.parameterobj.loadparameters(filename)
        self.parameterobj.update_other(self)
        return "OK"

    def savepars(self,filename=None):
        self.parameterobj.update_yourself(self)
        if filename is not None:
            self.parameterobj.saveparameters(filename)
        return "OK"

    def out_of_eta_range(self,e):

        if e < abs(self.eta_range) and e > -abs(self.eta_range):
            return True
        if e < -180.+abs(self.eta_range) or e > 180.-abs(self.eta_range):
            return True
        return False

    def assigntorings(self):
        """
        Assign the g-vectors to hkl rings
        """
        # rings are in self.unitcell
        limit = maximum.reduce(self.ds)
        print "Maximum d-spacing considered",limit
        self.unitcell.makerings(limit,tol=self.ds_tol)
        dsr=self.unitcell.ringds
        self.ra=zeros(self.gv.shape[0],Int)-1
        self.na=zeros(len(dsr),Int)
        print "Ring assignment array shape",self.ra.shape
        tol=float(self.ds_tol)
        for i in range(self.ra.shape[0]):
            # Assign the peak to a ring (or no ring)
            ds=self.ds[i]
            best=999.
            for j in range(len(dsr)):
                diff=abs(ds-dsr[j])
                if diff < tol:
                    if diff < best:
                        self.ra[i]=j
                        best=diff
        # Report on assignments
        ds=array(self.ds)
        print "Ring     (  h,  k,  l) Mult  total indexed to_index  "
        for j in range(len(dsr)):
            ind = compress( equal(self.ra,j), arange(self.ra.shape[0]) )
            self.na[j]=ind.shape[0]
            n_indexed  = sum(where( take(self.ga,ind) >  -1, 1, 0))
            n_to_index = sum(where( take(self.ga,ind) == -1, 1, 0))
            diffs = abs(take(ds,ind) - dsr[j])
            h=self.unitcell.ringhkls[dsr[j]][0]
            print "Ring %-3d (%3d,%3d,%3d)  %3d  %5d  %5d  %5d"%(j,h[0],h[1],h[2],len(self.unitcell.ringhkls[dsr[j]]),
                     self.na[j],n_indexed,n_to_index)
        # We will only attempt to index g-vectors which have been assigned to hkl rings (this gives a speedup if there
        # are a lot of spare peaks
        ind = compress( greater(self.ra,-1) , arange(self.ra.shape[0]) )
        self.gvr = take(self.gv , ind)
        print "Using only those peaks which are assigned to rings for scoring trial matrices"
        print "Shape of scoring matrix",self.gvr.shape
        self.gvflat=reshape(fromstring(self.gvr.tostring(),Float),self.gvr.shape) # Makes it contiguous in memory, hkl fast index
        return "OK"

    def friedelpairs(self,filename):
        """
        Attempt to identify Freidel pairs

        Peaks must be assigned to the same powder ring
        Peaks will be the closest thing to being 180 degrees apart
        """
        out = open(filename,"w")
        dsr=self.unitcell.ringds
        nring = len(dsr)
        for j in range( nring ):
            ind = compress( equal(self.ra,j), arange(self.ra.shape[0]) )
            # ind is the indices of the ring assigment array - eg which hkl is this gv
            #
            if len(ind)==0:
                continue
            thesepeaks = take(self.gv,ind)
            #
            h=self.unitcell.ringhkls[dsr[j]][0]
            #
            out.write("\n\n\n# h = %d \n"%(h[0]))
            out.write("# k = %d \n"%(h[1]))
            out.write("# l = %d \n"%(h[2]))
            out.write("# npks = %d \n"%(thesepeaks.shape[0]))
            out.write("# score eta1 omega1 tth1 gv1_x gv1_y gv1_z eta2 omega2 tth2 gv2_x gv2_y gv2_z\n")
            for k in range(thesepeaks.shape[0]):
                nearlyzero = thesepeaks + thesepeaks[k]
                mag = sum(nearlyzero*nearlyzero,1)
                b = argmin(mag)
                if b > k:
                    out.write("%f "%( sqrt(mag[b]) ) )
                    out.write("%f %f %f %f %f %f    "%(self.eta[k],self.omega[k],self.tth[k],self.gv[k][0],self.gv[k][1],self.gv[k][2]))
                    out.write("%f %f %f %f %f %f\n"%(self.eta[b],self.omega[b],self.tth[b],self.gv[b][0],self.gv[b][1],self.gv[b][2]))
            return "OK"



    def find(self):
        """
        Dig out the potential hits
        """
        # Which are the rings being used for indexing
        hkls1 = self.unitcell.ringhkls[self.unitcell.ringds[int(self.ring_1)]]
        hkls2 = self.unitcell.ringhkls[self.unitcell.ringds[int(self.ring_2)]]
        print "hkls of rings being used for indexing"
        print "Ring 1:",hkls1
        print "Ring 2:",hkls2
        cosangles=[]
        for h1 in hkls1:
            for h2 in hkls2:
                ca=self.unitcell.anglehkls(h1,h2)
                cosangles.append(ca[1])
        cosangles.sort()
        coses=[]
        while len(cosangles)>0:
            a=cosangles.pop()
            if abs(a-1.)<1e-5 or abs(a+1.)<1e-5: # Throw out 180 degree angles
                continue
            if len(coses)==0:
                coses.append(a)
                continue
            if abs(coses[-1]-a) > 1e-5:
                coses.append(a)
        print "Possible angles and cosines between peaks in rings:"
        for c in coses:
            print math.acos(c)*180/math.pi,c
        #
        # Need indices of gvectors to test
        iall = arange(self.gv.shape[0])
        #
        # Optionally only used unindexed peaks here? Make this obligatory
        i1 = compress(logical_and(equal(self.ra,self.ring_1), self.ga==-1  ) , iall).tolist()
        i2 = compress(logical_and(equal(self.ra,self.ring_2), self.ga==-1  ) , iall).tolist()
        print "Number of peaks in ring 1:",len(i1)
        print "Number of peaks in ring 2:",len(i2)
        print "Minimum number of peaks to identify a grain",self.minpks
        # print self.gv.shape
        ntry=0
        nhits=0
        self.hits=[]
        tol=float(self.cosine_tol)
        ng=0
        mp=sqrt(sum(self.gv*self.gv,1))
        # print mp.shape
        ps1 = take(self.gv,i1,0)
        mp1 = take(mp,i1,0)
        n1 = ps1.copy()
        ps2 = take(self.gv,i2,0)
        mp2 = take(mp,i2,0)
        n2 = ps2.copy()
        # print "mp1.shape",mp1.shape
        # print "n1[:,1].shape",n1[:,1].shape
        for i in range(3):
            n1[:,i]=n1[:,i]/mp1
            n2[:,i]=n2[:,i]/mp2
        cs = array(coses,Float)
        found=0
        hits=[]
        start = time.time()
        onepercent=len(i1)/100
        if onepercent < 1: onepercent=1
        start=time.time()
        for i in range(len(i1)):
            if i%onepercent == 0:
                print "Percent done %6.3f%%   ... potential hits %-6d \r"%(i*100./len(i1),len(hits)),
            costheta=matrixmultiply(n2,n1[i])
            best,diff = closest.closest(costheta,cs)
            if diff < tol:
                hits.append( [ diff, i1[i], i2[best] ])
        print "Percent done %6.3f%%   ... potential hits %-6d \r"%(i*100./len(i1),len(hits)),
        print
        print "Number of trial orientations generated",len(hits)
        print "Time taken",time.time()-start
        self.hits=hits
        return len(self.hits)
        
    def histogram_drlv_fit(self,UBI=None,bins=None):
        """
        Generate a histogram of |drlv| for a ubi matrix
        For use in validation of grains
        """
        if UBI is None:
            ubilist = self.ubis
        else:
            ubilist = [UBI]
        if bins is None:
            start=0.25
            fac=2
            bins=[start]
            while start > 1e-5:
                start=start/fac
                bins.append(start)
            bins.append(-start)
            bins.reverse()
            bins=array(bins)
        hist = zeros((len(ubilist),bins.shape[0]-1),Int)
        j=0
        for UBI in ubilist:
            h=matrixmultiply(UBI,transpose(self.gv))
            hint=floor(h+0.5).astype(Int) # rounds down
            diff=h-hint
            drlv=sort(sqrt(sum(diff*diff,0))) # always +ve
            if drlv[-1]>0.866:
                print "drlv of greater than 0.866!!!",drlv[-1]
            positions =  searchsorted(drlv,bins)
            hist[j,:] =  positions[1:]-positions[:-1]
            j=j+1
        #for i in range(bins.shape[0]-1):
        #   print "%10.7f - %10.7f   %10d"%(bins[i],bins[i+1],hist[i])
        #print sum(hist),hist.shape,bins.shape
        bins=bins.tolist()
        hist=hist.tolist()
        self.histogram=hist
        self.bins=bins
        print "ulula",self.bins[0],self.bins[1],self.bins[2],len(self.bins)
        return "OK"
        
    def scorethem(self):
        start=time.time()
        ts=0
        tor=0
        ng=0
        tol=float(self.hkl_tol)
        gv=self.gvflat
        all=len(self.hits)
        print "Scoring",all,"potential orientations"
        prog=0
        ng=0
        nuniq=0
        while len(self.hits) > 0 and ng <self.max_grains:
            sys.stdout.write("Tested %8d    Found %8d     Rejected %8d as not being unique\r"%(prog,ng,nuniq))
            prog=prog+1
            diff,i,j = self.hits.pop()
            if self.ga[i]>-1 or self.ga[j]>-1:  # skip things which are already assigned
                continue
            if i==j:
                continue
            try:
                t0=time.time()
#            print "\n\n",diff,i,j,self.gv[i,:],self.gv[j,:]
                self.unitcell.orient(self.ring_1, self.gv[i,:], self.ring_2, self.gv[j,:],verbose=0)
                UBI=self.unitcell.UBI
                t1=time.time()
                # n=self.score(UBI)
                # Function call overhead actually makes a big difference here
                n=closest.score(UBI,gv,tol)
                t2=time.time()
                tor=tor+t1-t0
                ts=ts+t2-t1
#            print self.ring_1,self.ring_2,n
            except:
                print i,j,self.ring_1,self.ring_2
                print self.gv[i]
                print self.gv[j]
                raise
            if n > self.minpks:
                # See if we already have this grain...
                try:
                    ubio=self.refine(self.unitcell.UBI.copy()) # refine the orientation
                    ind=self.getind(ubio) # indices of peaks indexed
                    ga=take(self.ga,ind)  # previous grain assignments
                    uniqueness=sum(where(ga==-1,1,0))*1.0/ga.shape[0]
                    if uniqueness > self.uniqueness:
                        put(self.ga,ind,len(self.scores)+1)
                        self.ubis.append(ubio)
                        self.scores.append(n)
                        ng=ng+1
                    else:
                        nuniq=nuniq+1
                    #            put(self.ga,ind,ng)
                except:
                    pass
        print
        print "Number of orientations with more than",self.minpks,"peaks is",len(self.ubis)
        print "Time taken",time.time()-start
        if len(self.ubis)>0:
            bestfitting=argmax(self.scores)
            print "UBI for best fitting\n",self.ubis[bestfitting]
            print "Unit cell\n",ubitocellpars(self.ubis[bestfitting])
            print "Indexes",self.scorelastrefined,"peaks, with <drlv2>=",self.fitlastrefined
            print "That was the best thing I found so far"
            notaccountedfor = sum(where( logical_and(self.ga==-1, self.ra!=-1),1,0))
            print "Number of peaks assigned to rings but not indexed = ",notaccountedfor
            #self.histogram(self.ubis[bestfitting])
        else:
            print "Try again, either with larger tolerance or fewer minimum peaks"
        return len(self.ubis)
    

    def saveindexing(self,filename,tol=None):
        """
        Save orientation matrices
        """
        f=open(filename,"w")
        i=0
        import math
        from ImageD11 import transform
        from LinearAlgebra import inverse
        for ubi in self.ubis:
            if tol==None:
                tol=self.hkl_tol
            h=matrixmultiply(ubi,transpose(self.gv))
            hint=floor(h+0.5).astype(Int) # rounds down
            gint=matrixmultiply(inverse(ubi),hint)
            diff=h-hint
            drlv2=sum(diff*diff,0)
            ind = compress( less(drlv2,tol*tol) , arange(self.gv.shape[0]) )
            try:
                mdrlv=  sum(sqrt(take(drlv2,ind)))/ind.shape[0]
            except:
                mdrlv= 1.0
            f.write("Grain: %d   Npeaks=%d   <drlv>=%f\n"%(i,ind.shape[0],mdrlv))
            i=i+1
            f.write("UBI:\n"+str(ubi)+"\n")
            cellpars = ubitocellpars(ubi)
            f.write("Cell pars: ")
            for abc in cellpars[:3]: f.write("%10.6f "%(abc))
            for abc in cellpars[3:]: f.write("%10.3f "%(abc))
            f.write("\n")
            f.write("Peak   (  h       k       l      )   drlv             x       y ")
            if self.wavelength < 0:
                f.write("\n")
            else:
                f.write("   Omega_obs Omega_calc   Eta_obs Eta_calc   tth_obs tth_calc\n")
                tc,ec,oc =  transform.uncompute_g_vectors(gint,self.wavelength,wedge=self.wedge)
            for j in ind:
                f.write("%-6d ( % 6.4f % 6.4f % 6.4f ) % 12.8f "%(j,h[0,j],h[1,j],h[2,j],sqrt(drlv2[j])) )
                f.write(" % 7.1f % 7.1f "%(self.xp[j],self.yp[j]) )
                if self.wavelength < 0:
                    f.write("\n")
                else:
                    # # # These should be equal to
                    to=math.asin(self.wavelength*self.ds[j]/2)*360/math.pi # tth observed
                    eo=self.eta[j]
                    oo=self.omega[j]
                    tc1=tc[j]
                    # Choose which is closest in eta/omega, there are two choices, {eta,omega}, {-eta,omega+180}
                    w=argmin( [ abs(ec[0][j] - eo) , abs(ec[1][j] - eo) ] )
                    ec1=ec[w][j]
                    oc1=oc[w][j]
                    # Now find best omega within 360 degree intervals
                    oc1=mod_360(oc1,oo)
                    f.write("  % 9.4f % 9.4f     % 9.4f % 9.4f   % 9.4f % 9.4f"% (oo,oc1, eo,ec1 ,to,tc1))
                if self.ra[j]==-1:
                    f.write(" *** was not assigned to ring\n")
                else:
                    f.write("\n")
            f.write("\n\n")
        # peaks assigned to rings
        in_rings = compress(greater(self.ra,-1),arange(self.gv.shape[0]))
        f.write("\n\nAnd now listing via peaks which were assigned to rings\n")
        nleft=0
        nfitted=0
        for peak in in_rings:
            # Compute hkl for each grain
            h=self.gv[peak,:]
            f.write("\nPeak= %-5d Ring= %-5d gv=[ % -6.4f % -6.4f % -6.4f ]   omega= % 9.4f   eta= % 9.4f   tth= % 9.4f\n"%(peak,self.ra[peak],h[0],h[1],h[2],
                  self.omega[peak],self.eta[peak],self.tth[peak]))
            m=0
            n=0
            bestubi=999.
            for ubi in self.ubis:
                hi = matrixmultiply(ubi,h)
                hint = floor(hi+0.5).astype(Int)
                gint = matrixmultiply(inverse(ubi),hint)
                diff=hi-hint
                drlv2 = sum(diff*diff,0)
                if drlv2 < bestubi:
                    bestubi=drlv2
                    besthi =hi
                    bestm=m
                if drlv2 < tol*tol:
                    f.write("Grain %-5d (%3d,%3d,%3d)"%(m,hint[0],hint[1],hint[2]))
                    f.write("  ( % -6.4f % -6.4f % -6.4f )  "%(hi[0],hi[1],hi[2]))
                    # hint
                    tt,e,o=transform.uncompute_one_g_vector(gint,self.wavelength,self.wedge)
#               print "obs",self.omega[peak],self.eta[peak],self.tth[peak]
#               print "calc",tt,e,o
                    w=[ abs(e[0] - self.eta[peak]) , abs(e[1] - self.eta[peak]) ]
                    w=argmin( w )
                    et=e[w]
                    om=o[w]
                    # Now find best omega within 360 degree intervals
                    om=mod_360(om,self.omega[peak])
                    f.write(" omega= % 9.4f   eta= %9.4f   tth= %9.4f\n"%(om,et,tt) )
                    n=n+1
                m=m+1
            if n==0:
                f.write("Peak not assigned, closest=[ % -6.4f % -6.4f % -6.4f ] for grain %d\n"%(besthi[0],besthi[1],besthi[2],bestm))
                nleft=nleft+1
            else:
                nfitted=nfitted+1

        f.write("\n\nTotal number of peaks was %d\n"%(self.gv.shape[0]))
        f.write("Peaks assigned to grains %d\n"%(nfitted))
        f.write("Peaks assigned to rings but remaining unindexed %d\n"%(nleft))

        f.write("Peaks not assigned to rings at all %d\n"%(sum(where(self.ra==-1,1,0))))
        f.close()
        return "OK"




    def getind(self,UBI,tol=None):
        """
        Returns the indices of peaks in self.gv indexed by matrix UBI
        """
        if tol==None:
            tol=self.hkl_tol
        h=matrixmultiply(UBI,transpose(self.gv))
        hint=floor(h+0.5).astype(Int) # rounds down
        diff=h-hint
        drlv2=sum(diff*diff,0)
        drlv2=where(self.ra==-1,tol+1,drlv2)
        ind = compress( less(drlv2,tol) , arange(self.gv.shape[0]) )
        return ind


    def score(self,UBI,tol=None):
        """
        Decide which are the best orientation matrices
        """
#      t0=time.time()
        if tol==None:
            return closest.score(UBI,self.gvflat,self.hkl_tol)
        else:
            return closest.score(UBI,self.gvflat,tol)
        t1=time.time()
        h=matrixmultiply(UBI,transpose(self.gv))
        hint=floor(h+0.5).astype(Int) # rounds down
        diff=h-hint
        drlv2=sum(diff*diff,0)
        tol = float(self.hkl_tol)
        tol = tol*tol
#      print "%e"%(tol)
#      for i in range(10):
#         print h[:,i],hint[:,i],drlv2[i]
        ind = compress( less(drlv2,tol) , arange(self.gv.shape[0]) )
#      ind = compress( less(drlv2[:npks],tol) , arange(npks) )
        t2=time.time()
        print n-len(ind),"Time in c",t1-t0,"Time in python",t2-t1
#      print "Grain UBI"
#      print UBI
#      print "Number of peaks",ind.shape[0]
        return ind

    def refine(self,UBI):
        """
        Refine an orientation matrix and rescore it.

        From Paciorek et al Acta A55 543 (1999)
        UB = R H-1
           where:
           R = sum_n r_n h_n^t
           H = sum_n h_n h_n^t
           r = g-vectors
           h = hkl indices
        """
#      print "Orientation and unit cell refinement of"
#      print "UBI\n",UBI
#      print "Scores before",self.score(UBI)
        # Need to find hkl indices for all of the peaks which are indexed
        h=matrixmultiply(UBI,transpose(self.gv))
        hint=floor(h+0.5).astype(Int) # rounds down
        diff=h-hint
        drlv2=sum(diff*diff,0)
        tol = float(self.hkl_tol)
        tol = tol*tol
        # Only use peaks which are assigned to rings for refinement
        ind = compress( logical_and(less(drlv2,tol),greater(self.ra,-1)) , arange(self.gv.shape[0]) )
        scoreb4=ind.shape[0]
        contribs = take(drlv2,ind)
        try:
            fitb4=sum(contribs)/contribs.shape[0]
        except:
            print "No contributing reflections for\n",UBI
            raise
        drlv2_old=drlv2
        R=zeros((3,3),Float)
        H=zeros((3,3),Float)
        for i in ind:
            r = self.gv[i,:]
            k = hint[:,i].astype(Float)
#           print r,k
            R = R + outerproduct(r,k)
            H = H + outerproduct(k,k)
        from LinearAlgebra import inverse
        try:
            HI=inverse(H)
            UBoptimal=matrixmultiply(R,HI)
            UBIo=inverse(UBoptimal)
        except:
            # A singular matrix - this sucks.
            UBIo=UBI
        h=matrixmultiply(UBIo,transpose(self.gv))
        hint=floor(h+0.5).astype(Int) # rounds down
        diff=h-hint
        drlv2=sum(diff*diff,0)
        ind = compress( logical_and(less(drlv2,tol),greater(self.ra,-1)), arange(self.gv.shape[0]) )
        self.scorelastrefined=ind.shape[0]
        contribs = take(drlv2,ind)
        try:
            self.fitlastrefined=math.sqrt(sum(contribs)/contribs.shape[0])
        except:
            print "\n\n\n"
            print "No contributing reflections for\n",UBI
            print "After refinement, it was OK before ???"
            print "\n\n\n"
            raise
#      for i in ind:
#         print "( %-6.4f %-6.4f %-6.4f ) %12.8f %12.8f"%(h[0,i],h[1,i],h[2,i],sqrt(drlv2[i]),sqrt(drlv2_old[i]))
#      print UBIo
#      print "Scores after", self.score(UBIo,self.hkl_tol)
#      print "diff\n",UBI-UBIo
#      print "Mean drlv now",sum(sqrt(drlv2))/drlv2.shape[0],
#      print "Mean drlv old",sum(sqrt(drlv2_old))/drlv2_old.shape[0]
        return UBIo

    def saveubis(self,filename):
        """
        Save the generated ubi matrices into a text file
        """
        f=open(filename,"w")
        for u in self.ubis:
            f.write("%f %f %f\n"  %(u[0,0],u[0,1],u[0,2]))
            f.write("%f %f %f\n"  %(u[1,0],u[1,1],u[1,2]))
            f.write("%f %f %f\n\n"%(u[2,0],u[2,1],u[2,2]))
        f.close()
        return "OK"

    def coverage(self):
        """
        Compute the expected coverage of reciprocal space
        use the min/max obs values of xp/yp/omega to work out what was measured in the scan?
        No lambda or
        """
        pass


    def readgvfile(self,filename):
        f=open(filename,"r")
        import unitcell,math
        # Lattice!!!
        self.unitcell = unitcell.cellfromstring(f.readline())
        while 1:
            line=f.readline()
            if line[0]=="#":
                if line.find("wavelength")>-1:
                    self.wavelength = float(line.split()[-1])
                    print "Got wavelength from gv file of ",self.wavelength
                    continue
                if line.find("wedge")>-1:
                    self.wedge = float(line.split()[-1])
                    print "Got wedge from gv file of ",self.wedge
                    continue
                if line.find("ds h k l")>-1:
                    continue   # reads up to comment line
                if line.find("omega")>-1:
                    break
        self.eta=[]   # Raw peak information
        self.omega=[]
        self.ds=[]
        self.xr=[]
        self.yr=[]
        self.zr=[]
        self.xp=[]
        self.yp=[]
        for line in f.xreadlines():
            try:
                v=[float(x) for x in line.split()]
                if self.out_of_eta_range(v[6]):
                    continue
                self.xr.append(v[0])
                self.yr.append(v[1])
                self.zr.append(v[2])
                self.xp.append(v[3])
                self.yp.append(v[4])
                self.ds.append(v[5])
                self.eta.append(v[6])
                self.omega.append(v[7])
            except:
                print line
                raise
#            raise "Problem interpreting the last thing I printed"
        f.close()
        if self.wavelength > 0:
            self.tth=arcsin(array(self.ds)*self.wavelength/2)*360/math.pi
        else:
            self.tth=zeros(len(self.ds))
        self.gv=transpose(array( [ self.xr , self.yr, self.zr ] ,Float))
        self.allgv = self.gv.copy()
        self.ga=zeros(len(self.ds),Int)-1 # Grain assignments

        self.gvflat=reshape(fromstring(self.gv.tostring(),Float),self.gv.shape) # Makes it contiguous in memory, hkl fast index
        print "Read your gv file containing",self.gv.shape
        return "OK"
    
    def plotxyz(self):
        """
        Gets gv from indexing object
        Plots the x,y,z (gv) array in a 3D opengl window
        """
        import plot3d
        gv = self.parent.guicommander.getdata("indexer","gv")
        if self.gv is not None:
            if self.plot3d==None:
                self.plot3d = plot3d.plot3d(self,self.gv)
                self.plot3d.go()
                print self.plot3d
            else:
                self.plot3d.changedata(self.gv)
        return "OK"
#      if self.wavelength>0:
#         print "First ten peaks"
#         from ImageD11 import transform
#         import math
#         if self.gv.shape[0]>10:
#            all=10
#         else:
#            all=self.gv.shape[0]
#         to,eo,oo=transform.uncompute_g_vectors(transpose(self.gv)[:all,:],self.wavelength)
#         print "Peak tth_calc tth_gv_obs eta_obs eta_gv_obs_1 eta_gv_obs_1 omega_obs omega_gv_obs omega_gv_obs"
#         for i in range(all):
#            tc=math.asin(self.ds[i]*self.wavelength/2)*360/math.pi
#            print i,tc,to[i],self.eta[i],eo[0][i],eo[1][i],self.omega[i],oo[0][i],oo[1][i]
#         print  "...."