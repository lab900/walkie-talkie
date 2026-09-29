import numpy as np, sounddevice as sd, sys
idx=[i for i,d in enumerate(sd.query_devices()) if "blackhole" in d["name"].lower()][0]
sr=48000; t=np.arange(int(sr*1.5))/sr; tone=(0.3*np.sin(2*np.pi*440*t)).astype(np.float32)
for k in range(2):
    rec=sd.playrec(np.repeat(tone[:,None],2,1),sr,channels=2,device=(idx,idx),blocking=True)[:,0]
    print(sys.argv[1] if len(sys.argv)>1 else "", k, "peak", round(float(np.abs(rec).max()),3), "nonzero", int((rec!=0).sum()))
