import { Router } from 'express';
import { LogCompressor } from '../memory/log-compressor.js';

const router = Router();
const compressor = new LogCompressor();

// Start the scheduled job when module loads (or via explicit start call in index)
// We'll export the instance to start it in index.ts
export const logCompressor = compressor;

/**
 * POST /api/memory/compress
 * Trigger manual log compression
 */
router.post('/compress', async (req, res) => {
    try {
        console.log('Triggering manual logs compression...');
        await compressor.compressNow();
        res.json({ message: 'Compression cycle started.' });
    } catch (error: any) {
        console.error('Compression trigger failed:', error);
        res.status(500).json({ error: error.message });
    }
});

export const memoryRouter = router;
