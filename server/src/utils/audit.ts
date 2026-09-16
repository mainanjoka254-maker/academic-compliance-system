import type { Request } from "express";
import { prisma } from "../lib/prisma.js";

export async function writeAudit(params: {
  req?: Request;
  userId?: string | null;
  action: string;
  entity?: string;
  entityId?: string;
  metadata?: unknown;
}) {
  await prisma.auditLog.create({
    data: {
      userId: params.userId ?? params.req?.user?.id ?? null,
      action: params.action,
      entity: params.entity,
      entityId: params.entityId,
      ip: params.req?.ip,
      userAgent: params.req?.get("user-agent") ?? undefined,
      metadata: params.metadata as object | undefined,
    },
  });
}
