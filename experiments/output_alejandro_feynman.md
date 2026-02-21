## <span id="page-0-0"></span>A short derivation of Feynman formula

Alejandro Rivero <sup>∗</sup>

Dep. F´ısica Te´orica, Universidad de Zaragoza, 50009 Zaragoza, Spain

August 23, 2018

## Abstract

The complex exponential weighting of Feynman formalism is seen to happen at the classical level. (Finiteness of) Feynman path integral formula is suspected then to appear as a consistency condition for the existence of certain Dirac measures over functional spaces.

1. The simplest variational problems can be easily formulated in terms of distribution theory. For instance, recall the static problem, to find the minimum of a function and evaluate some quantity in that minimum. We can reformulate it as: Given a function f(x), find a Dirac measure δ<sup>f</sup> concentrated in the critical points of f.

The answer is obviously δ(f ′ (x)). Its exponential form,

$$\langle \delta(f'(x))|g(x)\rangle = \int \int e^{izf'(x)}g(x)dzdx = \int \int \lim_{y \to x} e^{iz\frac{f(y) - f(x)}{y - x}}g(x)dzdx \quad (1)$$

is interesting for itself, but we can carry it to a more amazing shape by making the substitution ǫ = y−x z . Then the previous limit is asymptotically equivalent to

$$<\delta_f|g> = \int \int \lim_{\epsilon \to 0} e^{i\frac{1}{\epsilon}(f(y) - f(x))} g(x) dx \frac{dy}{\epsilon}$$
 (2)

This is done controlling x − y and the oscillating character of the exponential.

Now, if f has only an extremal point, we can choose to work with the "halved" expression,

$$<\delta_f^{1/2}|O> = \lim_{\epsilon \to 0} \frac{1}{\epsilon^{1/2}} \int e^{i\frac{1}{\epsilon}f(x)} O(x) dx$$
 (3)

from which we can recover (2) by taking modulus square,

$$<\delta_f|g> = <\delta_f^{1/2}|O> <\delta_f^{1/2}|O>^*,$$
 (4)

with g(x) = O(x)O<sup>∗</sup> (x). Of course, other games are possible, changing the regularization method - i.e. the role of ǫ -, but all of them are equivalent in the vicinity of ǫ = 0.

The whole point here is that the basic structure of path integral, the complex exponential weighting, is already present in the integral presentation of the most elementary variational problem, the principle of virtual work, which we teach in general physics courses.

It is intriguing to notice that Dirac guessed the exponential weighting directly from quantum mechanics, trying to build contact transformations [\[3\]](#page-2-0), instead of uplifting it from its classical version, as we are doing here.

<sup>∗</sup>rivero@sol.unizar.es

<span id="page-1-0"></span>2. To go from the zero-dimensional problem (static) to the one dimensional (classical dynamics) we need to generalize (3) to spaces of functions of one variable, time. There we can not directly assert the convergence of the regularization, and we need to follow an indirect route, inspired in Wilson-Kogut triangles [8, ch. 12]. Feynman formula will appear as a convergence condition: the regularizated measure has a limit if and only if the Feynman measure over paths has a finite one.

First lets restate the question: We are given a functional  $L[\phi]$  and associated contour conditions  $(\phi_0, t_0), (\phi_1, t_1)$  determining a space F of functions. The problem, again, is to find a Dirac measure over this space F concentrated in the critical points of the functional L. Inspired in (3), we propose as answer the limit of the discretized functional:

$$\langle \delta_L^{\epsilon,\epsilon'} | O[\phi] \rangle = \int \dots \int \frac{1}{\epsilon^{n/2}} e^{i\frac{1}{\epsilon}\epsilon' \sum_{i=0}^n L^{\epsilon'}[x_i, \frac{x_{i+1} - x_i}{\epsilon'}]} O[\phi](\Pi dx_i)$$
 (5)

Where  $\epsilon' = (t_1 - t_0)/(n+1)$ ,  $x_0 = \phi_0$ ,  $x_{n+1} = \phi_1$ , and we must take both limits  $\epsilon, \epsilon' \to 0$ . Each integration in  $dx_i$  is a mirror of formula (3), concentrating in the values of  $x_i$  where the function  $L[x_1, ...x_n]$ , takes its extremal value keeping the rest of  $\{x_i\}$  fixed.

At this point, we could directly define a proportionality constant between  $\epsilon$  and  $\epsilon'$ , say  $\epsilon = h\epsilon'$ , to join both limits and them claim (8) directly.

**3**. But better we would like to try a more sophisticated process, and ask ourselves about the convergence of the  $\epsilon, \epsilon' \to 0$  limit. To do it, we introduce an arbitrary scale h which controls the limit process: each term would be moved back according a transformation

$$\epsilon \to \tau_{\frac{\epsilon}{h}}(\epsilon), \epsilon' \to \tau_{\frac{\epsilon}{h}}(\epsilon'),$$
 (6)

whose exact form still elude us. Surely we must to take in account that, in addition to  $\epsilon, \epsilon'$ , also the quantities  $\xi_i \equiv x_{i+1} - x_i$  go to zero. In fact, Feynman proof of Schrödinger equation [4] relies heavyly in an approximation for small  $\xi$ . In our case, it is implied an adjustment in  $\xi$  which we can hide under the carpet of the Lagrangian.

On the other side, transformation (6) reduces the number n of points where we fix the classical path. So, alternatively, we could try to build  $\epsilon \to 0$  as a discrete series of bipartitions  $\epsilon_{n+1} = \epsilon_n/2$ , and then the control as a block summation back to the expression of level  $\epsilon_0 = h$ .

4. In any case, the limit would be convergent if and only if the controlled series

$$\langle \delta_L^{h,\epsilon'} | O[\phi] \rangle = \int \dots \int \frac{1}{(h\epsilon')^{n/2}} e^{i\frac{1}{h}L_n^{\epsilon'}[\phi_0, x_1, \dots x_n, \phi_1]} O[\phi](\Pi dx_i)$$
 (7)

converges (compare with the control of a Wiener measure through the normalized brownian bridge, see e.g. [7, sec. 3.1.2]).

Notice that the limit of this second series is Feynman path integral formula,

$$<\delta^{h,0}|O> = \int e^{i\frac{1}{h}S[\phi]}O[\phi](d\phi),$$
 (8)

as searched. Note also that our indirect travel gives the normalization factor  $(h\epsilon)^{\frac{1}{2}}$  almost directly from (3). Feynman [4] prefers to get it in the course of its approximation for small  $\xi$ .

Finally, note that the constant h we have introduced to control the series is arbitrary, and we can repeat the construction for any other value  $h = \epsilon'' > 0$ . In this form we get a third series

$$<\delta^{\epsilon''}|O> = \int e^{i\frac{1}{\epsilon''}S[\phi]}O[\phi](d\phi)$$
 (9)

<span id="page-2-0"></span>which is also a solution of the proposed regulatization problem, and additionally fulfills that it is invariant under the control transformation:

$$\tau_{\mu} < \delta^{h}| = <\delta^{\mu h}| \tag{10}$$

In the spirit of Wilson-Kogut transformations, we would like to call([5\)](#page-1-0),[\(7](#page-1-0)),([9\)](#page-1-0) respectively a bare series, a renormalized series, and the dressed series associated to the measure being defined.

The transformation which lets invariant the dressed series "corresponds to" Gell-Mann old RG transformation, its invariants being associated to some mean value equations. For instance, we could "formally" manipulate eq [\(8](#page-1-0)) for O = δL/δφ and then we get

$$\langle \frac{\delta L}{\delta \phi} \rangle = \int e^{i\frac{1}{h}L[\phi]} \frac{\delta L}{\delta \phi} d\phi = \int e^{i\frac{1}{h}L[\phi]} dL = \delta(\frac{1}{h})$$
 (11)

which is obviously invariant under the transformation. RG invariance in this context relates to Ehrenfest theorem.

5. As a final remark, let us to note that the derivation here exposed could be nicely formulated in the framework of the tangent grupoid of the configuration space as defined by Connes [2] (see also [1, 5] and references therein). Elements of tangent grupoid can be "chained" as arrays of vectors (x, x1)(x1, x2)(x2, x3)...(xn, y), functions over them are operator kernels such that (ab)(x<sup>i</sup> , xk) = R a(x<sup>i</sup> , xk)b(xk, x<sup>j</sup> )dxk. More, Connes grupoid relates to the grupoid of paths only if we make a scaling (x, y, ǫ) → (x, y, 2ǫ) after composition of arrows.

A deeper understanding of this framework would be useful before to try to generalize the construction to dimensions higher than one. For dim > 1 we would expect more exotic fixed points, and additional entities (fermions?) are surely needed in order to keep the properties of line integration, and stokes-like theorems, that usually are codifyed inside the wedge product of differentials. Also, known issues related to the kind of metric (Euclidean, Minkowski...) should become more relevant.

This work has been inspired from discussions with the theoretical teams of Zaragoza University and Costa Rica university, whose patience the author wants to thank. Partial support from project MEC.xxx.yyy must be acknowledged.

This document is a working draft. Comments are welcome, but please check the database [6] for more recent work in the subject

## References

- [1] J.F. Cari˜nena et al. Connes's Tangent Grupoid and Deformation Quantization, preprint [math/9802102](http://arxiv.org/abs/math/9802102)
- [2] A. Connes, Non Commutative Geometry, Academic Press 1994
- [3] P.A.M. Dirac, The Lagrangian in Quantum Mechanics, Phisik. Zeitschr. der Sowjetunion, 3, p. 64, 1933
- [4] R.P. Feynman, Space-Time Approach to Non-relativistic Quantum Mechanics, Rev. Mod. Phys. 20, 2, p. 357, 1948
- [5] A. Rivero, Introduction to the tangent grupoid, preprint [dg-ga/9710026](http://arxiv.org/abs/dg-ga/9710026)
- [6] [http://xxx.lanl.gov/find/math,](http://xxx.lanl.gov/find/math)physics/1/Rivero/0/1/0/1998/3/0
- [7] G. Roepstorff, Path Integral Approach to Quantum Physics, Springer TMP.
- [8] K.G. Wilson and J. Kogut, Phys Rep 12, 2, p. 75 (1974)