import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { Telegraf } from 'telegraf';
import { OpenaiService } from '../openai/openai.service';

@Injectable()
export class BotService implements OnModuleInit, OnModuleDestroy {
  private bot!: Telegraf;

  constructor(private readonly openaiService: OpenaiService) {}

  onModuleInit() {
    // 1) Initialize Telegraf
    this.bot = new Telegraf(process.env.BOT_TOKEN!);

    // 2) /start handler
    this.bot.start((ctx) => ctx.reply('👋 Choose language: /en /ru /uz'));

    // 3) /rate_essay handler
    this.bot.command('rate_essay', async (ctx) => {
      const fullText = ctx.message?.text || '';
      const essay = fullText.replace(/^\/rate_essay\s*/, '').trim();
      if (!essay) {
        return ctx.reply(
          '❗️ Usage: /rate_essay <your essay text up to 400 words>'
        );
      }

      await ctx.reply('⏳ Rating your essay...');

      try {
        const userLang = 'en';
        const result = await this.openaiService.rateEssay(essay, userLang);
        const jsonString = JSON.stringify(result, null, 2);
        await ctx.replyWithMarkdown('```json\n' + jsonString + '\n```');
      } catch (err) {
        console.error('OpenAI error:', err);
        await ctx.reply(
          '⚠️ Sorry, something went wrong while rating your essay.'
        );
      }
    });

    // 4) Launch polling
    this.bot.launch().then(() => {
      console.log('✅ Bot launched (Nest polling, /rate_essay ready).');
    });
  }

  onModuleDestroy() {
    this.bot.stop('SIGTERM');
  }
}
