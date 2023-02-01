# pnap lab information

## windows VM running ixia client 
    (RDP with u: arista, p: arastra)
	ixs342

## devices (ssh with u: admin, no password)
    2x 7280SR "ISP" switches
        hs423
        hs424

    2x 7280CR3 spines
        smd501
        smd505

    2x 7050X3 leaf switches
        cal383
        cal384
        cal385
        cal388

    2x harness (sits between MLAG / EVPN-AA pairs and ixia)
        do420
        do421

## connections
### 400G:
        smd501 et33,35 --- (2x) --- smd501 et34,36 
        smd505 et33,35  --- (2x) --- smd505 et34,36     
### 100G:
        hs423 et49 — smd501 et 1
        hs424 et49 --- smd505 et 1
        smd501 et2-6 --- (5x) --- smd505 et2-6 
        smd501 et7 --- cal383 et49
        smd501 et8 --- cal384 et49
        smd501 et9 --- cal385 et49
        smd501 et10 --- cal388 et49
        smd505 et7 --- cal383 et50
        smd505  et8 — cal384 et50
        smd505 et9 --- cal385 et50
        smd505 et10 --- cal388 et50
        cal383 et51,52  --- (2x) --- cal384 et51,52 
        cal385 et51,52 --- (2x) --- cal388 et51,52 

 ### 10G:
        cal383 et1 --- do420 et1
        cal384 et1 --- do420 et 2
        cal385 et1 --- do421 et1
        cal388 et1 — do421 et2
        ixia --- do420 et 3
        ixia --- do421 et 3
