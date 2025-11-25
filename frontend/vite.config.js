import { defineConfig, loadEnv } from 'vite'

export default ({ mode }) => {
  // load .env files and merge into process.env
  const env = loadEnv(mode, process.cwd(), '')
  process.env = { ...process.env, ...env }

  const host = process.env.VITE_HOST || 'localhost'

  return defineConfig({
    server: {
      host,
    },
  })
}
