C     Last change:  BB    5 Apr 2016    6:16 pm
	subroutine bouts(N,omega,LP0,CP,C1,D0P,DLP,D0,DL,DL1,LN,LNP1
     s,SP,LA0,pressn
     s,AANCHE,ISTYLE,LEVEE,NDEGG,NTESSG,IFLUTE,LEVRES,PAREMB,RHOA,ETA
     s,zboub,LP,zboup,L,zboue,clinte,cloute)
c...pour calculer les impédances d'extrémité et les corrections de
c...longueur internes.
c...arguments en sortie : zboub,LP,zboup,L,zboue,clinte,cloute
c...............................................................
c...zboub est l'impédance du bas du tube
c...LP est le tableau de la longueur des tronçons latéraux, corrigés
c...de la correction de longueur interne.
c...zboup est le tableau de l'impédance d'extrémité des cheminées
c...latérales (supposées ouvertes).
c...L est le tableau de la longueur des tronçons de la ligne, corrigés
c...de la correction de longueur interne au niveau du trou 
c...d'embouchure (flûtes).
c...zboue est l'impédance d'extrémité du trou d'embouchure (flûtes).
c...CLINTE et CLOUTE sont les corrections de longueur interne et externe
c...à l'embouchure (flûtes). CLINTE est une correction liée au 
c...raccordement de l'onde entre la cheminée d'embouchure et la perce ppale.
c...CLINTE est pris en compte explicitement dans le calcul de l'impédance.
c...CLOUTE est une correction de longueur extérieure, prise en compte
c...implicitement via l'impédance extérieure à l'embouchure. Ici, on ne
c...calcule CLOUTE que pour pouvoir imprimer sa valeur dans le fichier
c...de sortie de tutt.
c.................................................................
        INTEGER*4 ISTYLE
        REAL LP0,LN,LNP1,LA0,LP,LPC,L,LEVEE
        REAL LEVRES,LCHEM
        COMPLEX JC,zboub,zboubo,zboup,zboue,zboutc
        DIMENSION LP0(1),CP(1),ISTYLE(1),LEVEE(1),LP(1),L(1)
        DIMENSION D0(1),DL(1),D0P(1),DLP(1),SP(1),pressn(1)
        DIMENSION zboup(1)
	JC=(0.,1.)
c...calcul de l'impédance du bas du tube
	call lczbb(DL1,omega,rhoa,eta,zboubo)
        zboub=(1.-C1)*zboubo+jc*1.e10*c1
c...        WRITE(6,28) zboub
28      FORMAT(' impédance de bout =',2F10.5)
c...calcul de l'impédance d'extrémité des trous latéraux
        call lczb(LP0,CP,D0P,DLP,N,D0,DL,SP,ISTYLE,LEVEE,iflute,pressn,
     s omega,rhoa,eta,LP,zboup)
c...        WRITE(6,16) (LP0(I),LP(I),zboup(j),j=1,N)
16      FORMAT(' dans bouts LP0(I),LP(I),zboup=',4e12.5)
C...CALCUL DE LA CORRECTION DE LONGUEUR A L' EMBOUCHURE POUR CE
C...DEGRE DE LA GAMME.

	if(iflute) 54,51,52
c............................................................
c...Flûte traversière, embouchure décrite par 2 tronçons n° N et N+1
54      D0N=D0(N)
	DLN=DL(N)
	D0NP1=D0(N+1)
	DLNP1=DL(N+1)
	dtube=(D0(N-1)+DLP(N-1))/2.
        LCHEM=LN
        call lczbe(NDEGG,NTESSG,IFLUTE,D0N,DLN,D0NP1,DLNP1,
     SDTUBE,LCHEM,AANCHE,
     SLEVRES,PAREMB,omega,rhoa,eta,CLINTE,CLOUTE,ZBOUE)

c...La correction de longueur intérieure s'applique au tronçon n°N
c...La correction de longueur extérieure s'applique au tronçon n° N+1.
	L(N)=LN+CLINTE
	L(N+1)=CLOUTE
	go to 53
c...........................................................
c...Flûte à bec, embouchure décrite par un seul tronçon
51	D0N=D0(N)
	DLN=DL(N)
        D0NP1=LA0
	DLNP1=LA0
        dtube=(D0(N)+DLP(N))/2.
        LCHEM=0.5*LNP1
        call lczbe(NDEGG,NTESSG,IFLUTE,D0N,DLN,D0NP1,DLNP1,
     SDTUBE,LCHEM,AANCHE,
     SLEVRES,PAREMB,omega,rhoa,eta,CLINTE,CLOUTE,ZBOUE)
c...Les corrections de longueur intérieure et extérieure s'appliquent
c...au tronçon n° N+1
	L(N+1)=LNP1+CLINTE+CLOUTE
	go to 53
c.............................................................
c..Instrument à anche, pas de correction à l'embouchure.
c...cependant, on pourrait peut être en mettre une pour tenir compte des
c...résultats théoriques de Déc. 2006
52	continue
	clintE=0.
	cloutE=0.
c.............................................................
53 	continue
c...	write (6,17) CLINTE,CLOUTE
c...17      FORMAT(' CLINTE=',F10.5,' CLOUTE=', F10.5)
c.............................................................
        RETURN
        END

