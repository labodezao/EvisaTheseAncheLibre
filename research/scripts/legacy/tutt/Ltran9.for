C     Last change:  BB    5 Apr 2016    5:00 pm
        SUBROUTINE LTRANS(N,CP,C1,L,LP,S,SB,SP,DELTA,DELTAP,K,KP,RHOA
     S,OMEGA,MA,KA,FCM,FCP,AANCHE,zboup,zboue,zboub
     s,A,B,AP,BP,PEMB,WEMB,ZRV,ZIM)
C....
C...POUR CALCULER LA PARTIE IMAGINAIRE DE L' IMPEDANCE DU SYSTEME
C...ANCHE + TUBE: ZIM, ET LA REPARTITION DE PRESSION ET DE DEBIT
C...LE LONG DU TUBE.
c...
c...Le changement ltran7--->ltrans8 correspond à la prise en compte d'une
c...constante de propagation complexe dans les trous latéraux, différente
c...de celle de la perce principale (pour une meilleure description des
c...trous latéraux étroits).
C...Le changement ltrans8 ----> ltrans9 correspond à la prise en compte
c...d'une impédance d'extrémité complexe aux bouts ouverts pour décrire
c...le rayonnement et les pertes de charge localisées, et éviter les
c...corrections de longueur phénoménologiques utilisées jusque là.
c...
C...TOUS LES ARGUMENTS SONT EN ENTREE SAUF A,B,AP,BP,ZRV,ZIM,PEMB
C...ET WEMB.
C...
C...N=NB DE TROUS LATERAUX (OUVERTS OU FERMES) DE LA LIGNE (BOUT
C...MORT = TROU FERME COMPRIS).
C...N+1 EST AUSSI LE NB DE TRONCONS DE LA LIGNE.
C....
C...
C...L=TABLEAU DES LONGUEURS DE TRONCONS DU TUBE PPAL, EN PARTANT
C...DU BAS.
C...LES TRONCONS SONT SUPPOSES TRONCONIQUES; ILS PEUVENT ETRE LONGS
C...CAR ON TIENT COMPTE DES VARIATIONS SPATIALES DE PRESSION ET DE 
C...DEBIT DANS LES TRONCONS. ON FAIT COMME S' IL EXISTAIT UN TROU
C...(EVENTUELLEMENT TOUJOURS FERME) ENTRE CHAQUE TRONCON.
C....
C...LP=TABLEAU DES LONGUEURS EFFECTIVES DES LIGNES LATERALES
C...ASSOCIEES AUX TROUS (EN PARTANT DU BAS DU TUBE) COMPTE TENU DES
C...CORRECTIONS DE LONGUEUR EVALUEES PREALABLEMENT.
C...
C...LE TRONCONNEMENT DE LA LIGNE PEUT DECRIRE DEUX CHOSES DISTINCTES:
C...UN CHANGEMENT DANS LA  CONICITE OU LA SECTION DE LA PERCE, 
C...OU L' EXISTENCE D' UN 
C...TROU LATERAL. DANS TOUS LES CAS, LE PROGRAMME SUPPOSE L' EXISTENCE 
C...D' UNE BRANCHE LATERALE ENTRE CHAQUE TRONCON. L' INFLUENCE DE LA 
C...LIGNE LATERALE SERA NULLE SI LA SECTION SP(I) DE LA BRANCHE LATERALE
C...EST NULLE (CAS D' UN CHANGEMENT DE PERCE SANS VRAI TROU LATERAL).
C...DANS CE CAS, IL EST RECOMMANDE (MAIS PAS INDISPENSABLE) DE METTRE
C...AUSSI LP0(I)=0.
C...
C...CP EST UN TABLEAU QUI DIT SI LES TROUS SONT OUVERTS (0) OU 
C...OU FERMES (1). 
C...C1 DIT DE MEME SI LE BAS DE LA LT EST OUVERT OU FERME.
C...
C...S=TABLEAU DES SECTIONS DU TUBE PPAL (PERCE) A L' ORIGINE DE
C...CHAQUE TRONCON.
C...
C...LE COUPLAGE ENTRE L' INSTRUMENT ET LE MUSICIEN EST DECRIT ICI DE
C...LA MANIERE SUIVANTE: 1) IL PEUT Y AVOIR DES MODIFICATIONS
C...GEOMETRIQUES DE L' EMBOUCHURE, DUES AU MUSICIEN. PAR EXEMPLE,
C...LA COUVERTURE DU TROU D' EMBOUCHURE PAR LES LEVRES EST
C...DIFFERENTE ENTRE LE GRAVE ET L' AIGU POUR UNE FLUTE TRAVERSIERE.
C...ON EN REND COMPTE PAR LES DEUX PARAMETRES LEVRES ET PAREMB,
C...AGISSANT DANS LA SUROUTINE LCOREM QUI CALCULE LA CORRECTION  
C...DE LONGUEUR A L' EMBOUCHURE. 
C...                     2) IL PEUT AUSSI Y AVOIR DES MODIFICATIONS
C...DYNAMIQUES DUES AU MUSICIEN, QUI PEUT CHANGER LE COUPLAGE
C...ANCHE-TUYAU (DECRIT DANS LTRANS PAR LES PARAMETRES FCM ET FCP),
C...OU MODIFIER LES CARACTERISTIQUES DE L' ANCHE (MASSE ET RAIDEUR
C...EFFECTIVES, DECRITES DANS LE SS PGM ANCHE PAR LES PARAMETRES 
C...G0,G1,LA0,LA1,E0,E1,V0,V1,MA,KA).
C...S(N+1) EST LA SURFACE DU TROU D' EMBOUCHURE. RIEN N' EMPECHE DE
C...DECRIRE LA COUVERTURE DES LEVRES A L' EMBOUCHURE EN METTANT UN 
C...TUBE D' EMBOUCHURE DE SECTION VARIABLE. S(N+1) A ALORS UN SENS
C...PRECIS: C' EST LA SURFACE DU TROU D' EMBOUCHURE A SON EXTREMITE,
C...COMPTE TENU DE LA COUVERTURE DES LEVRES.
C...SP=                    DES TUBES LATERAUX
C...ATTENTION: LE BOUT MORT EST ASSIMILE A UN TROU BOUCHE DE HAUTEUR
C...LP(N)
C...L' EMBOUCHURE EST ASSIMILEE A UN TROU DE HAUTEUR L(N+1)
C...
C...K= TABLEAU DES CONSTANTES DE PROPAGATION DU SON DANS LES 
C...DIFFERENTS TRONCONS DE LA LIGNE ppale (K EST COMPLEXE, POUR TENIR
C...COMPTE DES PERTES VISCOTHERMIQUES). 
c...KP = tableau des constantes de propagation du son dans les
c...différents tronçons des lignes latérales.
c...
c...zboup est le tableau des impédances d'extrémité des trous latéraux
c...supposés ouverts (calculé dans la subroutine LCZB).
c...zboue et zboub sont respectivement l'impédance d'embouchure et
c...l'impédance de bas de ligne.
C...
C...LE SYSTEME PHYSIQUE MODéLISé EST UNE
C...COLONNE D' AIR RAMIFIEE EN ARETE DE POISSON, FERMEE A L'
C...EMBOUCHURE PAR UNE MEMBRANE SOUPLE modélisée comme un oscillateur
c...à un degré de liberté, DONT LES MOUVEMENTS SONT
C...COUPLES VIA LA RELATION: A(ANCHE)=FC*A(TUBE).
c...La membrane voit une impédance interne due à son couplage au
c...champ acoustique dans le tube, et une impédance externe due
c...au champ acoustique rayonné.
c...ON calcule l'impédance totale Z de l'anche couplée à ces deux champs.
C...
C...FC DECRIT LA FORCE DU COUPLAGE DE L' ANCHE AU TUYAU
C.. FC EST COMPLEXE: FC=FCM*CEXP(JC*FCP).
C...
C...SI FC=0, ON N' A PAS DE COUPLAGE A L' ANCHE: Z est L' IMPEDANCE
C...DU TUYAU SEUL. SI FC EST TRES GRAND, ON A AU CONTRAIRE
C...L' IMPEDANCE DE L' ANCHE SEULE sans couplage au tube.
C...
C...MA ET KA SONT LES PARAMETRES D' OSCILLATEUR DE L' ANCHE.
C...
C...Z EST L' IMPEDANCE DU SYSTEME LIGNE+ANCHE+espace extérieur, VUE DE L' ANCHE
C...PAR DEFINITION, Z = P(ANCHE)/W(ANCHE), OU P(ANCHE) EST LA 
C...PRESSION imposée SUR L' ANCHE
C...P(ANCHE)=FEXT/AANCHE, où AANCHE est  la surface vibrante de l'anche
C...ET OU W(ANCHE) EST LE DEBIT ENGENDRE PAR CETTE force imposée,
C...W(ANCHE)=V(ANCHE)*AANCHE
C...ZIM EST LA PARTIE IMAGINAIRE DE L' IMPEDANCE  A LA FREQ OMEGA.
c...
C...ON CALCULE LES FREQUENCES DE RESONANCE PASSIVES DU SYSTEME,
C...Les fréquences permises sont données par les ZEROS DE
c...la partie imaginaire de l'IMPEDANCE totale Z=Za+(Ztube+zboue)/fc.
C...CECI DECRIT EVIDEMMENT UNE FLUTE, MAIS AUSSI UNE CLARINETTE
C...SI ON PREND POUR DECRIRE L' ANCHE UNE MEMBRANE SUFFISAMMENT
C...RAIDE.
C...LE CRITERE de résonance  ZIM(OMEGA)=0 CORRESPOND au respect de l'équation
c...de la dynamique de l'anche oscillant en régime permanent.

c...Dans la plupart des cas pratiques, le couplage entre l'anche et le monde
c...extérieur est faible, et LA FACE EXTERNE DE LA MEMBRANE EST quasi LIBRE:
c...elle voit seulement l'impédance Zboue de son couplage à l'extérieur,
c...par exemple son impédance de rayonnement ou son impédance de couplage à la
c...cavité buccale. Les fréquences permises pour le système sont alors
c...proches des résonances du tube si les paramètres d'oscillateur de l'anche
c...sont petits (cas des anches aériennes, ie des flûtes); les fréquences permises
c...pour le système sont au contraire proches des antirésonances du tube si les
c...paramètres d'oscillateur de l'anche sont grands (cas de anches solides).
C...
C...A,B SONT DES TABLEAUX QUI PERMETTENT DE CALCULER PRESSION ET DEBIT
C...DANS LE TUBE PRINCIPAL, VIA LES RELATIONS SUIVANTES:
C...P(X,T)=(1/(1+DELTA*X))*(A*EXP(JC*K*X)+B*EXP(-JC*K*X)*EXP(JC*
C...OMEGA*T)
C...W(X,T)=-(S0/(JC*OMEGA*RHOA))*(A*(JC*K+DELTA(JC*K*X-1))*EXP(JC*K*X)
C...-B*(JC*K+DELTA(JC*K*X+1))*EXP(-JC*K*X))*EXP(JC*OMEGA*T)
C...AU POINT D' ABCISSE X DU
C...TRONCON, L' ORIGINE ETANT PRISE AU NOEUD I, IPRIME, I+1.
C...AP ET BP SONT LES TABLEAUX HOMOLOGUES POUR LES TRONCONS LATERAUX.
C...POUR CES DERNIERS, L' ORIGINE EST PRISE AU BOUT DE LA 
C...LIGNE OPPOSEE AU NOEUD.
C...PEMB ET WEMB SONT LES PRESSION ET DEBIT COMPLEXES A L' EMBOUCHURE
C....
C...CP(I)=0 ...........TROU I OUVERT
C...CP(I)=1 ...........TROU I FERME
C...
C...DELTA,DELTAP SONT LES TABLEAUX DONNANT LA CONICITE DU TRONCON:
C...DELTA=(DL-D0)/(D0*L)
C...
C...TOUTES LES UNITES SONT MKS.
C...
        IMPLICIT COMPLEX(T)
        REAL L,LP,MA,KA
        COMPLEX K,KP,A,B,AP,BP,JC,JKL1,JKLIP1,JKLPI
        COMPLEX PEMB,WEMB,ZT,ZA,FC,Z
        COMPLEX zboup, zboue, zboub
 
        DIMENSION CP(1),L(1),LP(1),S(1),SP(1),DELTA(1),DELTAP(1)
        DIMENSION K(1),A(1),B(1),AP(1),BP(1),KP(1),zboup(1)
C....
        PI=ACOS(-1.)
        JC=(0.,1.)
        JKL1=JC*K(1)*L(1)
        A(1)=CEXP(-JKL1)
C...LES A ET B SONT CALCULES A UNE CONSTANTE PRES. ON FIXE A(1)
C...A CETTE VALEUR ARBITRAIRE POUR DES RAISONS DE COMMODITE DE CALCUL.
        T13=JC*K(1)+DELTA(1)*(JKL1+1.)
        T14=JC*K(1)+DELTA(1)*(JKL1-1.)
        T15=SB*zboub/(jc*omega*rhoa)
        T16=1./(1.+DELTA(1)*L(1))
        T17=(T14*T15+T16)/(T13*T15-T16)
        T18=T14/T13
        B(1)=exp(JKL1)*(T17*(1.-C1)+T18*C1)
C...BOUCLE SUR LES TRONCONS
        DO 1 I=1,N
        JKLIP1=JC*K(I+1)*L(I+1)
        JKLPI=JC*KP(I)*LP(I)
C....
        TPIP1=EXP(JKLIP1)
        TMIP1=1./TPIP1
        TPPIP=EXP(JKLPI)
        TMPIP=1./TPPIP
C....CALCUL DES AP(I),BP(I).
        T20=JC*KP(I)-DELTAP(I)
        T21=JC*KP(I)+DELTAP(I)
        T22=zboup(I)*SP(i)/(jc*omega*rhoa)
        T3=(T20/T21)*CP(i)-(1.+T22*T20)/(1.-T22*T21)*(1.-CP(i))
        T1=(A(I)+B(I))*(1.+DELTAP(I)*LP(I))
        T4=TPPIP+TMPIP*T3
        AP(I)=T1/T4
        BP(I)=AP(I)*T3
C....CALCUL DES A(I+1),B(I+1).
        T5=(A(I)+B(I))*(1.+DELTA(I+1)*L(I+1))
        T6=S(I+1)*(JC*K(I+1)+DELTA(I+1)*(JKLIP1-1.))*TPIP1
        T7=S(I+1)*(JC*K(I+1)+DELTA(I+1)*(JKLIP1+1.))*TMIP1
        T8=SP(I)*(JC*KP(I)+DELTAP(I)*(JKLPI-1.))*TPPIP
        T9=SP(I)*(JC*KP(I)+DELTAP(I)*(JKLPI+1.))*TMPIP
        T10=S(I)*(A(I)*(JC*K(I)-DELTA(I))-B(I)*(JC*K(I)+DELTA(I)))
        T11=T10-AP(I)*T8+BP(I)*T9
        A(I+1)=(T11*TMIP1+T5*T7)/(T6*TMIP1+T7*TPIP1)
        B(I+1)=(T5-A(I+1)*TPIP1)*TPIP1
1       CONTINUE
C...CALCUL DE L' IMPEDANCE
        PEMB=A(N+1)+B(N+1)
        T12=A(N+1)*(JC*K(N+1)-DELTA(N+1))-B(N+1)*(JC*K(N+1)+DELTA(N+1))
        WEMB=-(S(N+1)/(JC*OMEGA*RHOA))*T12
        ZT=PEMB/WEMB
        FC=FCM*EXP(JC*FCP)
        ZA=JC*(MA*OMEGA-KA/OMEGA)/AANCHE**2
        IF(ABS(FCM).LT.0.00001) THEN
        Z=ZT+ZBOUE
        ELSE
        Z=ZA+(ZT+ZBOUE)/FC
        END IF
        ZIM=AIMAG(Z)
        zrv=AIMAG(jc*z)
C....       WRITE(6,100) ZA,ZT,Z,FCM
100     FORMAT('ZA=',2E8.1,'ZT=',2E8.1,'Z=',2E8.1,'FCM=',E8.1)
        RETURN
        END
        
