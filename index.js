import { ask } from './llm.js'
import { httpGet } from './tools.js'

const max_steps = 20
const tools = { httpGet }

async function loop(task) {
  let state = 'in_progress'
  let i = 0
  const messages = [
    {
      role: 'system',
      content:
        'You are an autonomous agent. Use tools as needed, then call finish when the task is complete.',
    },
    { role: 'user', content: task },
  ]

  while (i < max_steps && state !== 'done') {
    const response = await ask(messages)
    messages.push(response)

    if (response.tool_calls) {
      for (const call of response.tool_calls) {
        const args = JSON.parse(call.function.arguments)

        if (call.function.name === 'finish') {
          state = 'done'
          console.log(`Finished: ${args.summary}`)
          break
        }

        const fn = tools[call.function.name]
        const result = fn ? await fn(args.url) : `Unknown tool: ${call.function.name}`
        messages.push({ role: 'tool', tool_call_id: call.id, content: String(result) })
      }
    } else {
      console.log(`Response: ${response.content}`)
    }
    i++
  }

  if (state !== 'done') {
    console.log('Max steps reached without completing the task.')
  } else {
    console.log('Task completed successfully.')
  }
}

await loop('Fetch api.github.com with httpGet, tell me the page title, then call finish.')
