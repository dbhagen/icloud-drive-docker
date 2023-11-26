/* eslint-disable @typescript-eslint/no-var-requires */
/* eslint-disable global-require */
export default async function createSitemapRoutes() {
  const { $content } = require('@nuxt/content')
  const files = await $content({ deep: true }).only(['path']).fetch()

  return files.map((file: { path: string }) =>
    file.path === '/index' ? '/' : file.path,
  )
}
