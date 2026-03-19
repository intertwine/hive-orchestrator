import { buildWorkspaceContext, buildContextBlock } from "../services/project-context.js"
import { logger } from "../utils/logger.js"
import type { AgentHiveConfig } from "../types/index.js"

interface ChatMessage {
  role: string
  content: string
}

/** Inject Hive context into a chat message when a project is mentioned. */
export async function chatMessageHook(
  message: ChatMessage,
  config: Required<AgentHiveConfig>
): Promise<ChatMessage> {
  if (!config.injectContext) return message
  if (message.role !== "user") return message

  try {
    const contexts = await buildWorkspaceContext(config.basePath)
    const mentioned = contexts.find((c) =>
      message.content.toLowerCase().includes(c.projectId.toLowerCase())
    )
    if (!mentioned) return message

    const block = buildContextBlock(mentioned.projectId, mentioned.tasks)
    return {
      ...message,
      content: `${message.content}\n\n---\n${block}`,
    }
  } catch (err) {
    logger.warn("chatMessageHook: could not inject context")
    logger.debug(String(err))
    return message
  }
}
