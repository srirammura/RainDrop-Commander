import { NextRequest, NextResponse } from "next/server";
import { CommanderAgent } from "@/lib/commander-agent";
import { AuditRequest } from "@/lib/types";

export async function POST(request: NextRequest) {
  try {
    const body: AuditRequest = await request.json();

    if (!body.rule_description || !body.examples || body.examples.length === 0) {
      return NextResponse.json(
        { error: "rule_description and examples are required" },
        { status: 400 }
      );
    }

    const commander = new CommanderAgent(body.rule_description, body.examples);
    const result = await commander.auditRule();

    return NextResponse.json(result);
  } catch (error) {
    console.error("Audit error:", error);
    return NextResponse.json(
      {
        error: "Failed to audit rule",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

