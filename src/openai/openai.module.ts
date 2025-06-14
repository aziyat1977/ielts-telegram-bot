import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { OpenAI } from 'openai';

export const OPENAI_CLIENT = 'OPENAI_CLIENT';

@Module({
  imports: [ConfigModule],
  providers: [
    {
      provide: OPENAI_CLIENT,
      useFactory: (config: ConfigService) => {
        const key = config.get<string>('OPENAI_API_KEY');
        if (!key) throw new Error('Missing OPENAI_API_KEY');
        return new OpenAI({ apiKey: key });
      },
      inject: [ConfigService],
    },
  ],
  exports: [OPENAI_CLIENT],
})
export class OpenaiModule {}
