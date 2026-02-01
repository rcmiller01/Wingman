import { IncidentDetector } from './incident-detector.js';

let detector: IncidentDetector | null = null;

export function startDetector() {
    if (!detector) {
        detector = new IncidentDetector();
    }
    detector.start();
}

export function stopDetector() {
    if (detector) {
        detector.stop();
    }
}

export { IncidentDetector };
