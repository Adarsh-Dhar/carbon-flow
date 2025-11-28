import { createOpenAI } from "@ai-sdk/openai"
import { streamText } from "ai"

const openai = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY ?? "",
})

export async function POST(req: Request) {
  const { messages } = await req.json()

  if (!process.env.OPENAI_API_KEY) {
    return new Response(
      JSON.stringify({
        error: "OPENAI_API_KEY missing. Set it to enable live agent streaming.",
      }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    )
  }

  const result = streamText({
    model: openai(process.env.OPENAI_MODEL ?? "gpt-4o-mini"),
    system:
      "You are the Respiro Negotiator and Orchestrator agent. You collaborate with Sentry and Clinical agents to move high-risk calendar events, coordinate with families, and explain every action with calm authority.",
    messages,
    maxOutputTokens: 200,
  })

  return result.toUIMessageStreamResponse()
}

