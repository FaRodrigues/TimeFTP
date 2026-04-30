# TimeFTP-2P6

TimeFTP is the primary software tool used at the UTC (INXE) timescale to execute multiple tasks in parallel with executable subprograms embedded in the RxTools software package (provided by Septentrio). This program utilizes a Python feature called subprocess to call the following RxTools subprograms:
•	sbf2rin (that converts the proprietary Septentrio Binary File in RINEX);
•	rin2cgg (that converts RINEX in CGGTTS);
•	sbf2cgg (that converts the proprietary Septentrio Binary File in CGGTTS);
In addition, since the Python subprocess feature allows the calling with parameters of any executable program, we also automatize the R2CGGTTS (the software tool developed at the Royal Observatory of Belgium, in its version 8.3 and 8.8). In this way, the TimeFTP software works extending some functionalities that are not provided by the GNSS receiver manufacturer and other programs used in the routine calculations of a simple timescale. This software allows for the seamless integration of different proprietary systems, enabling the automation of both older GNSS receivers, such as the PolaRx3TR and PolaRx5TR models, and any other receiver with a programmable interface. The software incorporates SCP (Secure Copy Protocol) and FTP (File Transfer Protocol) communications and, in this way, we can send the RINEX, CGGTTS and CLOCK files to the TAI repository using FTP while we are able to send files to other repositories using SCP.
It is also important to note:
1.	The software is cross platform and so it works on both Windows and Linux;
2.	TimeFTP synchronizes its transmission with the last value of the STTIME column in the CGGTTS data, allowing data transmission at 16-minute intervals;
3.	The TimeFTP user interface is self-described in a XML file allowing the fast customization and adaptation;
4.	The software produces a log file for each MJD;
5.	The software can be customized to be used by another timescale, other NMI or even a client.

6.	
