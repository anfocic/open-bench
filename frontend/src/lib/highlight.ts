import { codeToHtml as shikiToHtml } from 'shiki';

export async function highlight(code: string, lang: string): Promise<string> {
  return shikiToHtml(code, {
    lang,
    themes: {
      dark: 'github-dark',
      light: 'github-light',
    },
    defaultColor: false,
  });
}