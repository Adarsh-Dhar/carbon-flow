import { createGoogleGenerativeAI } from "@ai-sdk/google"
import { convertToModelMessages, streamText } from "ai"

const gemini = createGoogleGenerativeAI({
  apiKey: process.env.GEMINI_API_KEY ?? "",
})

export async function POST(req: Request) {
  const { messages } = await req.json()
  const modelMessages = convertToModelMessages(messages ?? [])

  if (!process.env.GEMINI_API_KEY) {
    return new Response(
      JSON.stringify({
        error: "GEMINI_API_KEY missing. Set it to enable live agent streaming.",
      }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    )
  }

  const result = streamText({
    model: gemini(process.env.GEMINI_MODEL ?? process.env.OPENAI_MODEL ?? "models/gemini-2.5-flash"),
    system:
      "You are the Respiro Negotiator and Orchestrator agent. You collaborate with Sentry and Clinical agents to move high-risk calendar events, coordinate with families, and explain every action with calm authority.",
    messages: modelMessages,
    maxOutputTokens: 200,
  })

  return result.toUIMessageStreamResponse()
}

