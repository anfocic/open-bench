import { codeToHtml as shikiToHtml } from 'shiki';

const THEME = 'github-dark';

export async function highlight(code: string, lang: string): Promise<string> {
  return shikiToHtml(code, { lang, theme: THEME });
}
