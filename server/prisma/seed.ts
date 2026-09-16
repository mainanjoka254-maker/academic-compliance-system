import { PrismaClient } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

async function main() {
  const passwordHash = await bcrypt.hash("Admin@12345", 12);
  const admin = await prisma.user.upsert({
    where: { email: "admin@university.edu" },
    update: { passwordHash, firstName: "University", lastName: "Administrator", role: "ADMIN", isActive: true, emailVerified: true },
    create: {
      email: "admin@university.edu",
      passwordHash,
      firstName: "University",
      lastName: "Administrator",
      role: "ADMIN",
      isActive: true,
      emailVerified: true,
    },
  });

  await prisma.school.upsert({ where: { id: "school-demo" }, update: {}, create: { id: "school-demo", name: "School of Computing", code: "SOC" } });
  await prisma.department.upsert({ where: { id: "dept-demo" }, update: {}, create: { id: "dept-demo", name: "Information Systems", code: "IS", schoolId: "school-demo" } });
  await prisma.program.upsert({ where: { id: "program-demo" }, update: {}, create: { id: "program-demo", name: "Bachelor of Information Systems", code: "BIS", departmentId: "dept-demo", requiredCredits: 120 } });

  const rules = [
    ["min_attendance", "Minimum attendance", "Minimum attendance percentage", 75],
    ["min_gpa", "Minimum GPA", "Minimum semester GPA", 2],
    ["min_credit_hours", "Minimum credit hours", "Minimum registered credits per semester", 12],
    ["failed_core_courses", "Failed core courses", "Maximum serious core course failures", 2],
    ["missing_assessments", "Missing assessments", "Flag missing assessment marks", null],
    ["prerequisites", "Prerequisites", "Require completed prerequisites", null],
    ["required_registration", "Required registration", "Require current-semester registration", null],
  ] as const;
  for (const [key, name, description, threshold] of rules) {
    await prisma.complianceRule.upsert({
      where: { key },
      update: { name, description, threshold, enabled: true },
      create: { key, name, description, threshold, enabled: true },
    });
  }

  await prisma.userSettings.upsert({ where: { userId: admin.id }, update: {}, create: { userId: admin.id } });
  console.log("Seeded admin@university.edu / Admin@12345");
}

main().finally(() => prisma.$disconnect());
