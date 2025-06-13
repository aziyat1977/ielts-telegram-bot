import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
// Adjust this path if your BotModule lives elsewhere
import { BotModule } from '../bot/bot.module';

@Module({
  imports: [
    // Load .env and make ConfigService globally available
    ConfigModule.forRoot({ isGlobal: true }),

    // Your feature module
    BotModule,
  ],
})
export class AppModule {}
