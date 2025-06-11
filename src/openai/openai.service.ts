import { Injectable, InternalServerErrorException } from '@nestjs/common';
import OpenAI from 'openai';

@Injectable()
export class OpenaiService {
  private readonly client: OpenAI;

  constructor() {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new InternalServerErrorException('Missing OPENAI_API_KEY');
    }
    this.client = new OpenAI({ apiKey });
  }

  async rateEssay(essay: string, userLang?: string) {
    // Build the message array. We only use { role, content } entries.
    const messages: { role: 'system' | 'user'; content: string }[] = [
      {
        role: 'system',
        content:
          'You are an IELTS examiner (Writing Task 2). ' +
          'Output EXACTLY this JSON:\n' +
          '{\n' +
          '  "band": <1-9>,\n' +
          '  "criteria": { "TR": <0-9>, "CC": <0-9>, "LR": <0-9>, "GRA": <0-9> },\n' +
          '  "advice": <string>\n' +
          '}\n' +
          'If userLang is provided, translate the advice into that language.',
      },
      { role: 'user', content: essay },
    ];

    if (userLang) {
      // In v4, there is no `name` field—just repeat as "user" role.
      messages.push({ role: 'user', content: userLang });
    }

    try {
      const resp = await this.client.chat.completions.create({
  model: 'gpt-4o-mini',
  temperature: 0.2,
  messages,
});


      const content = resp.choices[0].message?.content;
      if (!content) {
        throw new Error('Empty response from OpenAI');
      }

      // Parse JSON (the API returns a JS object when format: 'json', but guard anyway)
      return typeof content === 'string' ? JSON.parse(content) : content;
    } catch (err: any) {
      throw new InternalServerErrorException(
        'OpenAI request failed: ' + err.message
      );
    }
  }
}
