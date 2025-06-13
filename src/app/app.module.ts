import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { BotModule } from './bot/bot.module'; // or wherever your BotModule lives

@Module({
  imports: [
    // ← Add this line:
    ConfigModule.forRoot({ isGlobal: true }),

    // your other feature modules
    BotModule,
    // ...
  ],
})
export class AppModule {}
