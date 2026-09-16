export function letterFromPercent(percent: number) {
  if (percent >= 70) return { letter: "A", points: 5 };
  if (percent >= 60) return { letter: "B", points: 4 };
  if (percent >= 50) return { letter: "C", points: 3 };
  if (percent >= 40) return { letter: "D", points: 2 };
  return { letter: "F", points: 0 };
}

export async function recomputeEnrollmentGrade(enrollmentId: string) {
  const { prisma } = await import("../lib/prisma.js");
  const enrollment = await prisma.enrollment.findUnique({
    where: { id: enrollmentId },
    include: {
      offering: { include: { assessments: { include: { marks: true } } } },
    },
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

  const percent = weighted / weightSum;
  const { letter, points } = letterFromPercent(percent);
  await prisma.grade.upsert({
    where: { enrollmentId },
    create: { enrollmentId, letter, points, percentage: percent },
    update: { letter, points, percentage: percent, updatedAt: new Date() },
  });
}
