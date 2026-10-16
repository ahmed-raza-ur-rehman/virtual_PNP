#include <stdio.h>
#include <math.h>
double fast_hypot(double, double);
double fast_dot(long, const double*, const double*);
int main() {
    printf("hypot(3,4)=%.6f\n", fast_hypot(3.0,4.0));
    double a[]={1,2,3}, b[]={4,5,6};
    printf("dot=%.6f\n", fast_dot(3,a,b));
    return 0;
}
