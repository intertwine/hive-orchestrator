const PREFIX = "[agent-hive]"

export const logger = {
  info: (msg: string) => console.log(`${PREFIX} ${msg}`),
  warn: (msg: string) => console.warn(`${PREFIX} WARN ${msg}`),
  error: (msg: string, err?: unknown) => {
    console.error(`${PREFIX} ERROR ${msg}`)
    if (err) console.error(err)
  },
  debug: (msg: string) => {
    if (process.env.AGENT_HIVE_DEBUG) console.debug(`${PREFIX} DEBUG ${msg}`)
  },
}
