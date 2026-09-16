INSERT INTO "School" (id, name, code, "createdAt") VALUES ('school-demo', 'School of Computing', 'SOC', NOW()) ON CONFLICT DO NOTHING;
INSERT INTO "Department" (id, name, code, "schoolId", "createdAt") VALUES ('dept-demo', 'Information Systems', 'IS', 'school-demo', NOW()) ON CONFLICT DO NOTHING;
INSERT INTO "Program" (id, name, code, "departmentId", "requiredCredits", "createdAt") VALUES ('program-demo', 'Bachelor of Information Systems', 'BIS', 'dept-demo', 120, NOW()) ON CONFLICT DO NOTHING;
INSERT INTO "ComplianceRule" (id, key, name, description, enabled, threshold, "updatedAt") VALUES ('rule-attendance', 'min_attendance', 'Minimum attendance', 'Minimum attendance percentage', true, 75, NOW()) ON CONFLICT DO NOTHING;
