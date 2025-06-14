import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { OpenaiModule } from '../openai/openai.module';
import { BotModule } from '../bot/bot.module';

@Module({
  imports: [
    // ① register ConfigService globally from your .env
    ConfigModule.forRoot({ isGlobal: true }),

    // ② make OpenaiService available everywhere
    OpenaiModule,

    // ③ bot logic (it can inject OpenaiService freely)
    BotModule,
  ],
})
export class AppModule {}
