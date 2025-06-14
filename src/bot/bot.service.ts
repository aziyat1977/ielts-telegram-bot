import { Injectable, Logger, OnModuleInit, Inject } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Telegraf } from 'telegraf';
import { OPENAI_CLIENT } from '../openai/openai.module';
import { OpenAI } from 'openai';

@Injectable()
export class BotService implements OnModuleInit {
  private readonly logger = new Logger(BotService.name);
  private bot: Telegraf;

  constructor(
    private readonly config: ConfigService,
    @Inject(OPENAI_CLIENT) private readonly openai: OpenAI,
  ) {}

  onModuleInit() {
    const token = this.config.get<string>('TELEGRAM_BOT_TOKEN');
    if (!token) throw new Error('Missing TELEGRAM_BOT_TOKEN');

    this.bot = new Telegraf(token);

    this.bot.start((ctx) => ctx.reply('👋 Hi, send me your IELTS answer!'));
    this.bot.on('text', async (ctx) => {
      const prompt = ctx.message.text;
      await ctx.reply('📝 Scoring…');

      const response = await this.openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [
          {
            role: 'system',
            content: this.config.get<string>('SYSTEM_PROMPT') ?? '',
          },
          { role: 'user', content: prompt },
        ],
      });

      await ctx.reply(response.choices[0].message.content.trim());
    });

    this.bot.launch().then(() => this.logger.log('✅ Bot launched'));
  }
}
