import type { ComplianceStatus, Prisma, RiskLevel } from "@prisma/client";
import { prisma } from "../../config/prisma.js";
import { letterFromPercentage } from "../../utils/grades.js";

export type RuleMap = Record<string, { enabled: boolean; threshold: number | null; config: Record<string, unknown> }>;

export async function loadRules(): Promise<RuleMap> {
  const rows = await prisma.complianceRule.findMany();
  const map: RuleMap = {};
  for (const r of rows) {
    map[r.key] = {
      enabled: r.enabled,
      threshold: r.threshold,
      config: (r.config as Record<string, unknown>) ?? {},
    };
  }
  return map;
}

function ruleOn(rules: RuleMap, key: string) {
  return rules[key]?.enabled !== false;
}

function thresh(rules: RuleMap, key: string, fallback: number) {
  const t = rules[key]?.threshold;
  return t == null ? fallback : t;
}

export async function recomputeEnrollmentGrade(enrollmentId: string) {
  const enrollment = await prisma.enrollment.findUnique({
    where: { id: enrollmentId },
    include: { offering: { include: { assessments: { include: { marks: true } } } } },
  });
  if (!enrollment) return;
  const assessments = enrollment.offering.assessments;
  if (!assessments.length) return;
  let weighted = 0;
  let weightSum = 0;
  let complete = true;
  for (const a of assessments) {
    const mark = a.marks.find((m) => m.studentId === enrollment.studentId);
    if (!mark) {
      complete = false;
      continue;
    }
    weighted += (mark.score / a.maxScore) * 100 * a.weight;
    weightSum += a.weight;
  }
  if (!complete || weightSum === 0) return;
  const percentage = weighted / weightSum;
  const { letter, points } = letterFromPercentage(percentage);
  await prisma.grade.upsert({
    where: { enrollmentId },
    create: { enrollmentId, letter, points, percentage },
    update: { letter, points, percentage },
  });
}

export async function evaluateStudent(studentId: string, semesterId: string) {
  const rules = await loadRules();
  const student = await prisma.student.findUnique({
    where: { id: studentId },
    include: {
      user: true,
      program: { include: { courses: true } },
      enrollments: {
        include: {
          grade: true,
          attendance: true,
          offering: {
            include: {
              course: { include: { prerequisites: true } },
              semester: true,
              assessments: { include: { marks: true } },
            },
          },
        },
      },
    },
  });
  if (!student) return null;

  const currentEnrollments = student.enrollments.filter((e) => e.offering.semesterId === semesterId);
  const allEnrollments = student.enrollments;

  const attendanceStats = currentEnrollments.flatMap((e) => e.attendance);
  const present = attendanceStats.filter((a) => a.status === "PRESENT" || a.status === "LATE" || a.status === "EXCUSED").length;
  const attendancePct = attendanceStats.length ? (present / attendanceStats.length) * 100 : 100;

  const graded = allEnrollments.filter((e) => e.grade);
  const gpaEnr = currentEnrollments.filter((e) => e.grade);
  const gpa = gpaEnr.length ? gpaEnr.reduce((s, e) => s + (e.grade?.points ?? 0), 0) / gpaEnr.length : 0;
  const cgpa = graded.length ? graded.reduce((s, e) => s + (e.grade?.points ?? 0), 0) / graded.length : 0;

  const failedCourses = graded.filter((e) => e.grade && e.grade.points < 2).length;
  const failedCores = graded.filter((e) => e.grade && e.grade.points < 2 && e.offering.course.isCore).length;

  let missingAssessments = 0;
  for (const e of currentEnrollments) {
    for (const a of e.offering.assessments) {
      if (!a.marks.some((m) => m.studentId === studentId)) missingAssessments += 1;
    }
  }

  const earnedCredits = graded.filter((e) => e.grade && e.grade.points >= 2).reduce((s, e) => s + e.offering.course.credits, 0);
  const requiredCredits = student.program.requiredCredits;
  const completionPct = requiredCredits ? Math.min(100, (earnedCredits / requiredCredits) * 100) : 0;

  const registeredCredits = currentEnrollments.reduce((s, e) => s + e.offering.course.credits, 0);
  const minCredits = thresh(rules, "min_credit_hours", 12);

  const passedCodes = new Set(graded.filter((e) => e.grade && e.grade.points >= 2).map((e) => e.offering.courseId));
  let missingPrereqs = 0;
  for (const e of currentEnrollments) {
    for (const p of e.offering.course.prerequisites) {
      if (!passedCodes.has(p.prerequisiteId) && p.prerequisiteId !== e.offering.courseId) missingPrereqs += 1;
    }
  }

  const coreProgramCourses = student.program.courses.filter((c) => c.isCore);
  const registeredIds = new Set(currentEnrollments.map((e) => e.offering.courseId));
  const missingCore = coreProgramCourses.filter((c) => {
    const taken = allEnrollments.some((e) => e.offering.courseId === c.id);
    return !taken && !registeredIds.has(c.id);
  }).length;

  const pendingCourses = currentEnrollments.filter((e) => !e.grade).length;

  const violations: { key: string; message: string; severity: string }[] = [];

  if (ruleOn(rules, "min_attendance") && attendancePct < thresh(rules, "min_attendance", 75)) {
    violations.push({
      key: "min_attendance",
      message: `Attendance below required threshold (${attendancePct.toFixed(1)}%).`,
      severity: "high",
    });
  }
  if (ruleOn(rules, "min_gpa") && gpa > 0 && gpa < thresh(rules, "min_gpa", 2)) {
    violations.push({ key: "min_gpa", message: `Semester GPA ${gpa.toFixed(2)} is below the minimum requirement.`, severity: "high" });
  }
  if (ruleOn(rules, "min_credit_hours") && registeredCredits < minCredits) {
    violations.push({
      key: "min_credit_hours",
      message: `Registered credit hours (${registeredCredits}) are below the required minimum.`,
      severity: "medium",
    });
  }
  if (ruleOn(rules, "failed_core_courses") && failedCores >= thresh(rules, "failed_core_courses", 2)) {
    violations.push({
      key: "failed_core_courses",
      message: `Student has failed ${failedCores} core courses.`,
      severity: "high",
    });
  }
  if (ruleOn(rules, "missing_assessments") && missingAssessments > 0) {
    violations.push({
      key: "missing_assessments",
      message: `Missing CAT/assignment/exam marks detected (${missingAssessments}).`,
      severity: "medium",
    });
  }
  if (ruleOn(rules, "prerequisites") && missingPrereqs > 0) {
    violations.push({
      key: "prerequisites",
      message: `Prerequisite requirement not satisfied (${missingPrereqs} missing).`,
      severity: "high",
    });
  }
  if (ruleOn(rules, "required_registration") && currentEnrollments.length === 0) {
    violations.push({ key: "required_registration", message: "Required course registration is missing for the current semester.", severity: "high" });
  }

  const high = violations.filter((v) => v.severity === "high").length;
  const medium = violations.filter((v) => v.severity === "medium").length;
  let status: ComplianceStatus = "COMPLIANT";
  if (high >= 2 || (high >= 1 && failedCores >= 2)) status = "NON_COMPLIANT";
  else if (high >= 1) status = "AT_RISK";
  else if (medium >= 1) status = "PARTIALLY_COMPLIANT";

  const maxIssues = 8;
  const issueScore = Math.min(maxIssues, high * 2 + medium);
  const compliancePct = Math.max(0, Math.round(100 - (issueScore / maxIssues) * 100));

  let riskLevel: RiskLevel = "LOW";
  if (status === "NON_COMPLIANT" || high >= 2) riskLevel = "HIGH";
  else if (status === "AT_RISK" || high >= 1 || gpa > 0 && gpa < 2.5) riskLevel = "MEDIUM";

  const details: Prisma.InputJsonValue = {
    violations,
    registeredCredits,
    earnedCredits,
    requiredCredits,
    missingAssessments,
    missingPrereqs,
    missingCore,
    gpa,
    cgpa,
  };

  const record = await prisma.complianceRecord.upsert({
    where: { studentId_semesterId: { studentId, semesterId } },
    create: {
      studentId,
      semesterId,
      status,
      riskLevel,
      compliancePct,
      gpa,
      cgpa,
      attendancePct,
      completionPct,
      failedCourses,
      pendingCourses,
      details,
    },
    update: {
      status,
      riskLevel,
      compliancePct,
      gpa,
      cgpa,
      attendancePct,
      completionPct,
      failedCourses,
      pendingCourses,
      details,
      computedAt: new Date(),
    },
  });

  await prisma.academicAlert.deleteMany({ where: { studentId, type: { startsWith: "COMPLIANCE_" } } });
  for (const v of violations) {
    await prisma.academicAlert.create({
      data: {
        studentId,
        type: `COMPLIANCE_${v.key.toUpperCase()}`,
        message: v.message,
        severity: v.severity,
      },
    });
    const userId = student.userId;
    await prisma.notification.create({
      data: {
        userId,
        title: "Compliance alert",
        body: v.message,
        type: "compliance",
      },
    });
  }

  return record;
}

export async function evaluateAllStudents(semesterId?: string) {
  const semester =
    (semesterId
      ? await prisma.semester.findUnique({ where: { id: semesterId } })
      : await prisma.semester.findFirst({ where: { isCurrent: true } })) ??
    (await prisma.semester.findFirst({ orderBy: { startsOn: "desc" } }));
  if (!semester) return { evaluated: 0 };
  const students = await prisma.student.findMany({ select: { id: true } });
  for (const s of students) {
    await evaluateStudent(s.id, semester.id);
  }
  return { evaluated: students.length, semesterId: semester.id };
}

export async function recomputeStudentCompliance(studentId: string) {
  const semester =
    (await prisma.semester.findFirst({ where: { isCurrent: true } })) ??
    (await prisma.semester.findFirst({ orderBy: { startsOn: "desc" } }));
  if (!semester) return null;
  return evaluateStudent(studentId, semester.id);
}

export async function recomputeAll(semesterId?: string) {
  const result = await evaluateAllStudents(semesterId);
  return result.evaluated;
}
