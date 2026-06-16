import { writable, type Writable, get } from 'svelte/store';

export enum MediaStreamStatusEnum {
    INIT = "init",
    CONNECTED = "connected",
    DISCONNECTED = "disconnected",
}
export const onFrameChangeStore: Writable<{ blob: Blob }> = writable({ blob: new Blob() });

export const mediaDevices = writable<MediaDeviceInfo[]>([]);
export const mediaStreamStatus = writable(MediaStreamStatusEnum.INIT);
export const mediaStream = writable<MediaStream | null>(null);

// Labels containing these strings are NDI virtual cameras — skip them
const NDI_LABELS = ['ndi', 'newtek', 'ndi webcam', 'ndi video', 'ndi hx'];

function isNdiDevice(device: MediaDeviceInfo): boolean {
    const label = device.label.toLowerCase();
    return NDI_LABELS.some(kw => label.includes(kw));
}

export const mediaStreamActions = {
    async enumerateDevices() {
        await navigator.mediaDevices.enumerateDevices()
            .then(devices => {
                const cameras = devices.filter(
                    device => device.kind === 'videoinput' && !isNdiDevice(device)
                );
                mediaDevices.set(cameras);
            })
            .catch(err => {
                console.error(err);
            });
    },
    async start(mediaDevicedID?: string) {
        // If no device specified, use the first real (non-NDI) camera
        if (!mediaDevicedID) {
            const allDevices = await navigator.mediaDevices.enumerateDevices();
            const realCam = allDevices.find(
                d => d.kind === 'videoinput' && !isNdiDevice(d)
            );
            if (realCam) mediaDevicedID = realCam.deviceId;
        }
        const constraints = {
            audio: false,
            video: {
                width: { ideal: 1024 },
                height: { ideal: 1024 },
                deviceId: mediaDevicedID ? { exact: mediaDevicedID } : undefined
            }
        };

        await navigator.mediaDevices
            .getUserMedia(constraints)
            .then((stream) => {
                mediaStreamStatus.set(MediaStreamStatusEnum.CONNECTED);
                mediaStream.set(stream);
            })
            .catch((err) => {
                console.error(`${err.name}: ${err.message}`);
                mediaStreamStatus.set(MediaStreamStatusEnum.DISCONNECTED);
                mediaStream.set(null);
            });
    },
    async startScreenCapture() {
        const displayMediaOptions = {
            video: {
                displaySurface: "window",
            },
            audio: false,
            surfaceSwitching: "include"
        };


        let captureStream = null;

        try {
            captureStream = await navigator.mediaDevices.getDisplayMedia(displayMediaOptions);
            const videoTrack = captureStream.getVideoTracks()[0];

            console.log("Track settings:");
            console.log(JSON.stringify(videoTrack.getSettings(), null, 2));
            console.log("Track constraints:");
            console.log(JSON.stringify(videoTrack.getConstraints(), null, 2));
            mediaStreamStatus.set(MediaStreamStatusEnum.CONNECTED);
            mediaStream.set(captureStream)
        } catch (err) {
            console.error(err);
        }

    },
    async switchCamera(mediaDevicedID: string) {
        if (get(mediaStreamStatus) !== MediaStreamStatusEnum.CONNECTED) {
            return;
        }
        const constraints = {
            audio: false,
            video: { width: { ideal: 1024 }, height: { ideal: 1024 }, deviceId: { exact: mediaDevicedID } }
        };
        await navigator.mediaDevices
            .getUserMedia(constraints)
            .then((stream) => {
                mediaStreamStatus.set(MediaStreamStatusEnum.CONNECTED);
                mediaStream.set(stream)
            })
            .catch((err) => {
                console.error(`${err.name}: ${err.message}`);
            });
    },
    async stop() {
        navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
            stream.getTracks().forEach((track) => track.stop());
        });
        mediaStreamStatus.set(MediaStreamStatusEnum.DISCONNECTED);
        mediaStream.set(null);
    },
};