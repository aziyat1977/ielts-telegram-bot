import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { OpenaiModule } from '../openai/openai.module';
import { BotModule } from '../bot/bot.module';

@Module({
  imports: [
    // 1) Load .env and register ConfigService globally
    ConfigModule.forRoot({ isGlobal: true }),

    // 2) Bring in the global OpenaiModule (provides OpenaiService + ConfigService)
    OpenaiModule,

    // 3) Your bot logic (which uses OpenaiService)
    BotModule,
  ],
})
export class AppModule {}
