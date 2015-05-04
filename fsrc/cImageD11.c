

#include <math.h>


/* subroutine assign( ubi, gv, tol, drlv2, labels, ig, n)
    implicit none
    real(8), intent(in) :: ubi(3,3), gv(3,n), tol
    integer, intent(in) :: n, ig
    integer, intent(inout) :: labels(n)
    real(8), intent(inout) :: drlv2(n) */

void assign( double ubi[3][3], double gv[][3], double tol,
	     double drlv2[], int labels[], int ig, int n);


void assign( double ubi[3][3], double gv[][3], double tol,
	     double drlv2[], int labels[], int ig, int n){
  /*    real(8) :: dr, h(3), ttol, dh(3)
	integer :: i */
  int i;
  double dr, h[3], ttol, dh[3];
  ttol = tol * tol;
  // !$omp parallel do private(h,dr,dh)
#pragma omp parallel for private(h,dr,dh)
  //  do i=1,n
  for(i=0;i<n;i++){
    /*       h(1)=ubi(1,1)*gv(1,i) + ubi(1,2)*gv(2,i) + ubi(1,3)*gv(3,i) 
	     h(2)=ubi(2,1)*gv(1,i) + ubi(2,2)*gv(2,i) + ubi(2,3)*gv(3,i) 
	     h(3)=ubi(3,1)*gv(1,i) + ubi(3,2)*gv(2,i) + ubi(3,3)*gv(3,i) */
    h[0] = ubi[0][0]*gv[i][0] + ubi[1][0]*gv[i][1] + ubi[2][0]*gv[i][2] ;
    h[1] = ubi[0][1]*gv[i][0] + ubi[1][1]*gv[i][1] + ubi[2][1]*gv[i][2] ;
    h[2] = ubi[0][2]*gv[i][0] + ubi[1][2]*gv[i][1] + ubi[2][2]*gv[i][2] ;
    // dh = abs(floor(h+0.5) - h)
    dh[0] = fabs(floor(h[0]+0.5) - h[0]);
    dh[1] = fabs(floor(h[1]+0.5) - h[1]);
    dh[2] = fabs(floor(h[2]+0.5) - h[2]);
    dr =  dh[0] + dh[1] + dh[2];
    dr = dr * dr;
    //    if ( (dr.lt.tol) .and. (dr.lt.drlv2(i)) ) then
    if ( (dr < ttol) && (dr < drlv2[i]) ) {
      drlv2[i] = dr;
      labels[i] = ig;
    }  else if (labels[i] == ig) {
      labels[i] = -1;
    } // endif
  } //    enddo
}  // end subroutine assign

/*
! compute_gv for refinegrains.py

subroutine compute_gv( xlylzl, omega, omegasign, wvln, wedge, chi, t, gv, n )
  use omp_lib
  implicit none
  real, intent(in) :: xlylzl(3,n), omega(n), wvln, wedge, chi, t(3)
  real(8), intent(inout):: gv(3,n)
  integer, intent(in) ::  n, omegasign
  real :: sc,cc,sw,cw,wmat(3,3),cmat(3,3), mat(3,3), u(3),d(3),v(3)
  real :: modyz, o(3), co, so, ds, k(3)
  real, parameter :: PI=3.141592653589793,RAD=PI/180.0,DEG=180.0/PI
  integer :: i

  ! Fill in rotation matrix of wedge, chi
  sw = sin(wedge*RAD)
  cw = cos(wedge*RAD)
  sc = sin(chi*RAD)
  cc = cos(chi*RAD)
  wmat = RESHAPE ((/ cw,0.,-sw,0.,1.,0.,sw,0.,cw /), (/3,3/))
  cmat = RESHAPE ((/ 1.,0.,0.,0.,cc,sc,0.,-sc,cc /), (/3,3/))
  mat = matmul(cmat, wmat)
!  write(*,*)'threads',omp_get_max_threads()
!  write(*,*)'mat',mat
!$omp parallel do private(so,co,u,o,d,modyz,ds,v,k)
  do i=1,n
     ! Compute translation + rotation for grain origin
     so = sin(RAD*omega(i)*omegasign)
     co = cos(RAD*omega(i)*omegasign)
     u(1) =  co*t(1) - so*t(2)
     u(2) =  so*t(1) + co*t(2)
     u(3) = t(3)
     ! grain origin, difference vec, |yz| component
     ! o = matmul(transpose(mat),u)
     o(1) = mat(1,1)*u(1)+mat(2,1)*u(2)+mat(3,1)*u(3)
     o(2) = mat(1,2)*u(1)+mat(2,2)*u(2)+mat(3,2)*u(3)
     o(3) = mat(1,3)*u(1)+mat(2,3)*u(2)+mat(3,3)*u(3)
     d = xlylzl(:,i) - o
     modyz  = 1./sqrt(d(1)*d(1) + d(2)*d(2) + d(3)*d(3))
     ! k-vector
     ds = 1./wvln
     k(1) = ds*(d(1)*modyz - 1. )
     k(2) = ds*d(2)*modyz
     k(3) = ds*d(3)*modyz
     v = matmul(mat,k)
     gv(1,i)= co*v(1) + so*v(2)
     gv(2,i)=-so*v(1) + co*v(2)
     gv(3,i)=v(3)
  enddo
 
end subroutine compute_gv



subroutine compute_xlylzl( s, f, p, r, dist, xlylzl, n )
! Computes laboratory co-ordinates
!
!
  implicit none
  real(8), intent(in) :: s(n), f(n)
  real(8), intent(in) :: p(4), r(3,3), dist(3)
  real(8), intent(inout):: xlylzl(3,n)
  integer, intent(in) ::  n
  ! parameters
  real(8) :: s_cen, f_cen, s_size, f_size
  ! temporaries
  real(8) :: v(3)
  integer :: i, j
  ! unpack parameters
  s_cen = p(1)
  f_cen = p(2)
  s_size = p(3)
  f_size = p(4)
  do i = 1, n
     ! Place on the detector plane accounting for centre and size
     ! subtraction of centre is done here and not later for fear of
     ! rounding errors
     v(1) = 0.0d0
     v(2) = (f(i) - f_cen)*f_size
     v(3) = (s(i) - s_cen)*s_size
     ! Apply the flip and rotation, python was :
     ! fl = dot( [[o11, o12], [o21, o22]], peaks=[[z],[y]] )
     ! vec = [0,fl[1],fl[0]]
     ! return dist + dot(rotmat, vec)
     do j = 1, 3
        ! Skip as v(1) is zero : r(1,j)*v(1)
        xlylzl(j,i) = r(2,j)*v(2) + r(3,j)*v(3) + dist(j)
     enddo
  enddo
end subroutine compute_xlylzl


! set LDFLAGS="-static-libgfortran -static-libgcc -static -lgomp -shared"  
! f2py -m fImageD11 -c fImageD11.f90 --opt=-O3 --f90flags="-fopenmp" -lgomp -lpthread
! export OMP_NUM_THREADS=12
! python tst.py ../test/nac_demo/peaks.out_merge_t200 ../test/nac_demo/nac.prm 
! python test_xlylzl.py ../test/nac_demo/peaks.out_merge_t200 ../test/nac_demo/nac.prm

! f2py -m fImageD11 -c fImageD11.f90 --f90flags="-fopenmp" -lgomp -lpthread  --fcompiler=gnu95 --compiler=mingw32 -DF2PY_REPORT_ON_ARRAY_COPY=1


gcc -fopenmp -Wall -c cImageD11.c

*/

