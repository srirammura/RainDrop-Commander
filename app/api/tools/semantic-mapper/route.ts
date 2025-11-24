import { NextRequest, NextResponse } from "next/server";
import { SemanticMapperTool } from "@/lib/tools/semantic-mapper";
import { AuditRequest } from "@/lib/types";

export async function POST(request: NextRequest) {
  try {
    const body: AuditRequest = await request.json();

    if (!body.rule_description || !body.examples) {
      return NextResponse.json(
        { error: "rule_description and examples are required" },
        { status: 400 }
      );
    }

    const tool = new SemanticMapperTool();
    const result = await tool.run(body.rule_description, body.examples);

    return NextResponse.json(result);
  } catch (error) {
    console.error("Semantic Mapper error:", error);
    return NextResponse.json(
      {
        error: "Failed to run semantic mapper",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

