from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from mailings.models import Client, Message, Mailing


class Command(BaseCommand):
    help = 'Создает тестовые данные для проверки работы приложения'

    def handle(self, *args, **options):
        self.stdout.write('Создание тестовых данных...\n')

        # Создание клиентов
        self.stdout.write('Создание клиентов...')
        clients = []
        clients_data = [
            {
                'email': 'ivanov@example.com',
                'full_name': 'Иванов Иван Иванович',
                'comment': 'Постоянный клиент'
            },
            {
                'email': 'petrov@example.com',
                'full_name': 'Петров Петр Петрович',
                'comment': 'Новый клиент'
            },
            {
                'email': 'sidorov@example.com',
                'full_name': 'Сидоров Сидор Сидорович',
                'comment': 'VIP клиент'
            },
            {
                'email': 'kozlov@example.com',
                'full_name': 'Козлов Алексей Викторович',
                'comment': ''
            },
            {
                'email': 'smirnova@example.com',
                'full_name': 'Смирнова Мария Александровна',
                'comment': 'Корпоративный клиент'
            },
        ]

        for client_data in clients_data:
            client, created = Client.objects.get_or_create(
                email=client_data['email'],
                defaults={
                    'full_name': client_data['full_name'],
                    'comment': client_data['comment']
                }
            )
            clients.append(client)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Создан клиент: {client.full_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  - Клиент уже существует: {client.full_name}')
                )

        # Создание сообщений
        self.stdout.write('\nСоздание сообщений...')
        messages = []
        messages_data = [
            {
                'subject': 'Специальное предложение!',
                'body': 'Уважаемый клиент!\n\nПредлагаем вам воспользоваться специальным предложением - скидка 20% на все товары до конца месяца!\n\nС уважением,\nКоманда магазина'
            },
            {
                'subject': 'Новинки в каталоге',
                'body': 'Здравствуйте!\n\nВ нашем каталоге появились новые товары. Заходите посмотреть!\n\nЛучшие предложения ждут вас.\n\nС уважением,\nМагазин'
            },
            {
                'subject': 'Напоминание о заказе',
                'body': 'Добрый день!\n\nНапоминаем, что ваш заказ готов к получению.\n\nПожалуйста, заберите его в течение 3 дней.\n\nСпасибо за покупку!'
            },
        ]

        for msg_data in messages_data:
            message, created = Message.objects.get_or_create(
                subject=msg_data['subject'],
                defaults={'body': msg_data['body']}
            )
            messages.append(message)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Создано сообщение: {message.subject}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  - Сообщение уже существует: {message.subject}')
                )

        # Создание рассылок
        self.stdout.write('\nСоздание рассылок...')
        now = timezone.now()

        mailings_data = [
            {
                'message': messages[0],
                'start_time': now + timedelta(hours=1),
                'end_time': now + timedelta(days=7),
                'recipients': clients[:3]
            },
            {
                'message': messages[1],
                'start_time': now - timedelta(hours=2),
                'end_time': now + timedelta(days=3),
                'recipients': clients[1:4]
            },
            {
                'message': messages[2],
                'start_time': now - timedelta(days=5),
                'end_time': now - timedelta(days=1),
                'recipients': clients[2:]
            },
        ]

        for idx, mailing_data in enumerate(mailings_data, 1):
            # Проверяем, существует ли похожая рассылка
            existing = Mailing.objects.filter(
                message=mailing_data['message'],
                start_time=mailing_data['start_time']
            ).first()

            if existing:
                self.stdout.write(
                    self.style.WARNING(f'  - Рассылка #{existing.pk} уже существует')
                )
                continue

            mailing = Mailing.objects.create(
                message=mailing_data['message'],
                start_time=mailing_data['start_time'],
                end_time=mailing_data['end_time']
            )
            mailing.recipients.set(mailing_data['recipients'])
            mailing.update_status()

            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Создана рассылка #{mailing.pk} '
                    f'({mailing.message.subject}) - Статус: {mailing.status}'
                )
            )

        # Итоговая статистика
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('\nТестовые данные успешно созданы!\n'))
        self.stdout.write(f'Клиентов: {Client.objects.count()}')
        self.stdout.write(f'Сообщений: {Message.objects.count()}')
        self.stdout.write(f'Рассылок: {Mailing.objects.count()}')
        self.stdout.write('=' * 60 + '\n')

        self.stdout.write(
            self.style.WARNING(
                'Теперь вы можете запустить сервер и посмотреть результат:\n'
                'python manage.py runserver\n'
            )
        )
