import type { RiskLevel } from "@prisma/client";
import { env } from "../../config/env.js";
import { prisma } from "../../config/prisma.js";
import { writeAudit } from "../../middleware/audit.js";

export type AnalysisInput = {
  studentName: string;
  gpa: number;
  cgpa: number;
  attendancePct: number;
  failedCourses: number;
  pendingCourses: number;
  compliancePct: number;
  violations: { key: string; message: string; severity: string }[];
  courseLoad: number;
};

export type AnalysisResult = {
  riskLevel: RiskLevel;
  explanation: string;
  recommendations: string[];
  source: "llm" | "local";
};

function localAnalyze(input: AnalysisInput): AnalysisResult {
  let score = 0;
  const reasons: string[] = [];
  if (input.attendancePct < 75) {
    score += 3;
    reasons.push("attendance has fallen below the required threshold");
  } else if (input.attendancePct < 85) {
    score += 1;
    reasons.push("attendance is approaching the minimum threshold");
  }
  if (input.gpa > 0 && input.gpa < 2) {
    score += 3;
    reasons.push("semester GPA is below the minimum requirement");
  } else if (input.gpa > 0 && input.gpa < 2.5) {
    score += 1;
    reasons.push("semester GPA is close to academic probation criteria");
  }
  if (input.failedCourses >= 2) {
    score += 3;
    reasons.push(`performance in ${input.failedCourses} courses is below the minimum requirement`);
  } else if (input.failedCourses === 1) {
    score += 1;
    reasons.push("one course has been failed");
  }
  if (input.pendingCourses >= 2) {
    score += 1;
    reasons.push("multiple assessments or grades are still outstanding");
  }
  const highV = input.violations.filter((v) => v.severity === "high");
  if (highV.length) {
    score += highV.length;
    reasons.push(highV[0].message.replace(/\.$/, "").toLowerCase());
  }

  let riskLevel: RiskLevel = "LOW";
  if (score >= 5) riskLevel = "HIGH";
  else if (score >= 2) riskLevel = "MEDIUM";

  const explanation =
    reasons.length === 0
      ? `${input.studentName} is classified as LOW RISK because attendance, GPA, and course completion currently meet institutional requirements.`
      : `${input.studentName} is classified as ${riskLevel} RISK because ${reasons.slice(0, 3).join(" and ")}.`;

  const recommendations: string[] = [];
  if (input.attendancePct < 85) recommendations.push("Improve attendance and attend additional academic support sessions.");
  if (input.gpa > 0 && input.gpa < 2.5) recommendations.push("Consult the lecturer and seek academic advising.");
  if (input.failedCourses > 0) recommendations.push("Retake a failed course where institutionally permitted.");
  if (input.pendingCourses > 0) recommendations.push("Complete missing assessments as soon as possible.");
  if (!recommendations.length) recommendations.push("Maintain current study habits and continue meeting program requirements.");

  return { riskLevel, explanation, recommendations, source: "local" };
}

async function llmAnalyze(input: AnalysisInput): Promise<AnalysisResult | null> {
  if (!env.ai.apiKey) return null;
  const prompt = `You are an academic compliance advisor. Analyze this student snapshot and return JSON only:
{"riskLevel":"LOW|MEDIUM|HIGH","explanation":"one paragraph","recommendations":["..."]}
Data: ${JSON.stringify(input)}
Rules: advisory only. Explain clearly. Risk HIGH if attendance < 75 or two+ failed cores or GPA < 2.`;

  const res = await fetch(`${env.ai.baseUrl.replace(/\/$/, "")}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.ai.apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: env.ai.model,
      temperature: 0.2,
      messages: [
        { role: "system", content: "Return valid JSON only." },
        { role: "user", content: prompt },
      ],
    }),
  });
  if (!res.ok) return null;
  const data = (await res.json()) as { choices?: { message?: { content?: string } }[] };
  const content = data.choices?.[0]?.message?.content ?? "";
  const jsonStart = content.indexOf("{");
  const jsonEnd = content.lastIndexOf("}");
  if (jsonStart < 0 || jsonEnd < 0) return null;
  const parsed = JSON.parse(content.slice(jsonStart, jsonEnd + 1)) as {
    riskLevel?: string;
    explanation?: string;
    recommendations?: string[];
  };
  const risk = (parsed.riskLevel ?? "MEDIUM").toUpperCase();
  const riskLevel: RiskLevel = risk === "HIGH" || risk === "LOW" || risk === "MEDIUM" ? (risk as RiskLevel) : "MEDIUM";
  return {
    riskLevel,
    explanation: parsed.explanation ?? localAnalyze(input).explanation,
    recommendations: parsed.recommendations?.length ? parsed.recommendations : localAnalyze(input).recommendations,
    source: "llm",
  };
}

export async function analyzeStudent(studentId: string, actorId?: string) {
  const record = await prisma.complianceRecord.findFirst({
    where: { studentId },
    orderBy: { computedAt: "desc" },
    include: { student: { include: { user: true, enrollments: true } } },
  });
  if (!record) return null;
  const details = (record.details ?? {}) as { violations?: { key: string; message: string; severity: string }[] };
  const input: AnalysisInput = {
    studentName: `${record.student.user.firstName} ${record.student.user.lastName}`,
    gpa: record.gpa,
    cgpa: record.cgpa,
    attendancePct: record.attendancePct,
    failedCourses: record.failedCourses,
    pendingCourses: record.pendingCourses,
    compliancePct: record.compliancePct,
    violations: details.violations ?? [],
    courseLoad: record.student.enrollments.length,
  };
  const llm = await llmAnalyze(input).catch(() => null);
  const result = llm ?? localAnalyze(input);

  const rec = await prisma.aiRecommendation.create({
    data: {
      studentId,
      riskLevel: result.riskLevel,
      explanation: result.explanation,
      recommendations: result.recommendations,
      source: result.source,
    },
  });

  await prisma.complianceRecord.update({
    where: { id: record.id },
    data: { riskLevel: result.riskLevel },
  });

  await prisma.notification.create({
    data: {
      userId: record.student.userId,
      title: "New academic recommendation",
      body: result.explanation,
      type: "ai",
    },
  });

  await writeAudit({
    userId: actorId,
    action: "AI_RECOMMENDATION_GENERATED",
    entity: "AiRecommendation",
    entityId: rec.id,
    metadata: { studentId, source: result.source },
  });

  return rec;
}

export async function analyzeAll(actorId?: string) {
  const students = await prisma.student.findMany({ select: { id: true } });
  const created = [];
  for (const s of students) {
    const rec = await analyzeStudent(s.id, actorId);
    if (rec) created.push(rec);
  }
  return created;
}
