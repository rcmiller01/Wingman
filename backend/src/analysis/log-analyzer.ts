import { LogEntry } from '../adapters/docker.js';

export interface ExtractedError {
    signature: string;
    timestamp: Date;
    fullMessage: string;
}

export class LogAnalyzer {
    // Basic patterns for error detection
    // tailored to catch common keywords but avoid noise if possible
    private errorPatterns = [
        /\b(error|exception|fatal|panic)\b/i,
        /failed to/i,
        /connection refused/i,
        /timeout/i,
    ];

    public analyze(logs: LogEntry[]): ExtractedError[] {
        const extractedErrors: ExtractedError[] = [];

        for (const log of logs) {
            // Check content against patterns
            // We do NOT assume stderr is always error, as many apps log info to stderr
            const matches = this.errorPatterns.some(pattern => pattern.test(log.message));

            if (matches) {
                extractedErrors.push({
                    signature: log.message.substring(0, 255), // Use first 255 chars as signature
                    timestamp: log.timestamp,
                    fullMessage: log.message
                });
            }
        }

        return extractedErrors;
    }
}
