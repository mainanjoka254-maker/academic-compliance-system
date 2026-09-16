import PDFDocument from "pdfkit";
import { prisma } from "../../config/prisma.js";
import { writeAudit } from "../../middleware/audit.js";

export async function studentReportRows(filters: {
  departmentId?: string;
  programId?: string;
  semesterId?: string;
  status?: string;
  riskLevel?: string;
  q?: string;
}) {
  const semester =
    (filters.semesterId
      ? await prisma.semester.findUnique({ where: { id: filters.semesterId } })
      : await prisma.semester.findFirst({ where: { isCurrent: true } })) ??
    (await prisma.semester.findFirst({ orderBy: { startsOn: "desc" } }));

  const records = await prisma.complianceRecord.findMany({
    where: {
      semesterId: semester?.id,
      status: filters.status as never,
      riskLevel: filters.riskLevel as never,
      student: {
        programId: filters.programId,
        program: { departmentId: filters.departmentId },
        OR: filters.q
          ? [
              { regNo: { contains: filters.q, mode: "insensitive" } },
              { user: { firstName: { contains: filters.q, mode: "insensitive" } } },
              { user: { lastName: { contains: filters.q, mode: "insensitive" } } },
            ]
          : undefined,
      },
    },
    include: {
      student: { include: { user: true, program: { include: { department: true } } } },
      semester: { include: { academicYear: true } },
    },
    orderBy: { compliancePct: "asc" },
  });
  return records;
}

export function toCsv(rows: Record<string, unknown>[]) {
  if (!rows.length) return "No data\n";
  const headers = Object.keys(rows[0]);
  const escape = (v: unknown) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  return [headers.join(","), ...rows.map((r) => headers.map((h) => escape(r[h])).join(","))].join("\n");
}

export async function buildPdf(title: string, lines: string[]): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ margin: 48 });
    const chunks: Buffer[] = [];
    doc.on("data", (c) => chunks.push(c as Buffer));
    doc.on("end", () => resolve(Buffer.concat(chunks)));
    doc.on("error", reject);
    doc.fillColor("#0f2744").fontSize(18).text("AI-Driven Academic Compliance System");
    doc.moveDown(0.3);
    doc.fontSize(13).fillColor("#1f4e79").text(title);
    doc.moveDown();
    doc.fillColor("#222").fontSize(10);
    for (const line of lines) doc.text(line, { paragraphGap: 4 });
    doc.end();
  });
}

export async function logReport(userId: string, type: string, format: string, filters: unknown) {
  await prisma.reportJob.create({ data: { userId, type, format, filters: filters as object } });
  await writeAudit({ userId, action: "REPORT_GENERATED", entity: "ReportJob", metadata: { type, format } });
}
