import { NextRequest, NextResponse } from "next/server";
import { OverfitDetectorTool } from "@/lib/tools/overfit-detector";
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

    const tool = new OverfitDetectorTool();
    const result = await tool.run(body.rule_description, body.examples);

    return NextResponse.json(result);
  } catch (error) {
    console.error("Overfit Detector error:", error);
    return NextResponse.json(
      {
        error: "Failed to run overfit detector",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

