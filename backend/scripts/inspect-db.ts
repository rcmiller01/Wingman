
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
    const docs = await prisma.logSummaryDocument.findMany();
    console.log('--- DB SUMMARY DOCUMENTS ---');
    console.log(JSON.stringify(docs, null, 2));
    console.log('----------------------------');
}

main()
    .catch(console.error)
    .finally(() => prisma.$disconnect());
