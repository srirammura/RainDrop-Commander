import { GoogleGenerativeAI } from "@google/generative-ai";

const API_KEY = process.env.GEMINI_API_KEY;
const MODEL_NAME = "gemini-1.5-flash";

if (!API_KEY) {
  throw new Error("GEMINI_API_KEY environment variable is not set");
}

let genAI: GoogleGenerativeAI | null = null;

export function getGeminiClient(): GoogleGenerativeAI {
  if (!genAI) {
    genAI = new GoogleGenerativeAI(API_KEY);
  }
  return genAI;
}

export async function generateText(
  prompt: string,
  options?: {
    temperature?: number;
    maxTokens?: number;
  }
): Promise<string> {
  try {
    const client = getGeminiClient();
    const model = client.getGenerativeModel({ 
      model: MODEL_NAME,
      generationConfig: {
        temperature: options?.temperature ?? 0.7,
        maxOutputTokens: options?.maxTokens ?? 2048,
      },
    });

    const result = await model.generateContent(prompt);
    const response = await result.response;
    return response.text();
  } catch (error) {
    console.error("Gemini API error:", error);
    throw new Error(`Failed to generate text: ${error instanceof Error ? error.message : "Unknown error"}`);
  }
}

export async function generateJSON<T>(
  prompt: string,
  options?: {
    temperature?: number;
  }
): Promise<T> {
  try {
    const client = getGeminiClient();
    const model = client.getGenerativeModel({ 
      model: MODEL_NAME,
      generationConfig: {
        temperature: options?.temperature ?? 0.3,
        responseMimeType: "application/json",
      },
    });

    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();
    return JSON.parse(text) as T;
  } catch (error) {
    console.error("Gemini API error:", error);
    throw new Error(`Failed to generate JSON: ${error instanceof Error ? error.message : "Unknown error"}`);
  }
}

