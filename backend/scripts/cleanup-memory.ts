
import { PrismaClient } from '@prisma/client';
import fs from 'fs';
import path from 'path';

const prisma = new PrismaClient({
    datasources: {
        db: {
            url: process.env.DATABASE_URL?.replace('postgres:5432', 'localhost:5433') // Hack for host access
        }
    }
});

const KNOWLEDGE_PATH = path.join(process.cwd(), '../knowledge');

async function main() {
    console.log('🧹 Cleaning up failed summaries...');

    // Delete ALL from DB for testing
    const { count } = await prisma.logSummaryDocument.deleteMany({});
    console.log(`Deleted ${count} failed records from DB.`);

    // Delete files
    if (fs.existsSync(KNOWLEDGE_PATH)) {
        // Recursive find
        const deleteFailedFiles = (dir: string) => {
            const files = fs.readdirSync(dir);
            for (const file of files) {
                const fullPath = path.join(dir, file);
                const stat = fs.statSync(fullPath);
                if (stat.isDirectory()) {
                    deleteFailedFiles(fullPath);
                } else if (file.endsWith('.md')) {
                    const content = fs.readFileSync(fullPath, 'utf8');
                    if (content.trim() === 'Failed to generate summary.') {
                        fs.unlinkSync(fullPath);
                        console.log(`Deleted file: ${fullPath}`);
                    }
                }
            }
        };
        deleteFailedFiles(KNOWLEDGE_PATH);
    }
}

main()
    .catch(console.error)
    .finally(() => prisma.$disconnect());
