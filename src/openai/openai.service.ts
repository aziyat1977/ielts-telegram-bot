import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import OpenAI from 'openai';

@Injectable()
export class OpenaiService {
  private readonly client: OpenAI;

  constructor(
    private readonly configService: ConfigService,  // ← inject here
  ) {
    const apiKey = this.configService.get<string>('OPENAI_API_KEY');
    if (!apiKey) {
      throw new InternalServerErrorException('Missing OPENAI_API_KEY');
    }
    this.client = new OpenAI({ apiKey });
  }

  async rateEssay(essay: string, userLang?: string) {
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
      messages.push({ role: 'user', content: userLang });
    }

    try {
      const resp = await this.client.chat.completions.create({
        model: 'gpt-4o-mini',
        temperature: 0.2,
        messages,
      });
      const content = resp.choices[0].message?.content;
      if (!content) throw new Error('Empty response from OpenAI');
      return typeof content === 'string' ? JSON.parse(content) : content;
    } catch (err: any) {
      throw new InternalServerErrorException(
        'OpenAI request failed: ' + err.message,
      );
    }
  }
}
