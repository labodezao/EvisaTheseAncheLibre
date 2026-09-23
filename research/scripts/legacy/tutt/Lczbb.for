C     Last change:  BB    5 Apr 2016    3:27 pm
        SUBROUTINE LCZBB(DL1,omega,rhoa,eta,zboub)
C...
C...calcul de l'impédance d'extrémité du bas de la ligne
C...TOUS LES ARGUMENTS SONT EN ENTREE SAUF cette impédance ZBOUB
        REAL LPC
        complex zboub,zboutc
	SC=3.14*DL1**2/4.
        LPC=0.
        CALL zbout(omega,rhoa,ETA,DL1,LPC,SC,ZBOUTC)
        zboub=zboutc
c...	write(6,1) zboub
1	format(' zboub=',2e15.2)
        RETURN
        END

