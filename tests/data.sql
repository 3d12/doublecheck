/*
Doublecheck - A web-based chess game database.
Copyright (C) 2024 Nick Edner

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/
INSERT INTO user (username, password, role)
VALUES
  ('test', 'pbkdf2:sha256:50000$TCI4GzcX$0de171a4f4dac32e3364c7ddc7c14f3e2fa61f2d17574483f7ffbb431b4acb2f',3),
  ('other', 'pbkdf2:sha256:50000$kJPKsz6N$d2d4784f1b030a9761f5ccaeeaca413f27f2ecb76d6168407af962ddce849f79',3),
  ('admin', 'scrypt:32768:8:1$EYXUGT3AwZQLTkhk$47cf946dc0003763d1952dd9ca3676b99981d53245f00a4ff1293823d4b3cefa94294fd614b3b1664c7b19b504f74b84852eaab098530eeb69caff797d1b3f9e',6);

INSERT INTO post (title, body, author_id, created)
VALUES
  ('test title', 'test' || x'0a' || 'body', 1, '2018-01-01 00:00:00'),
  ('test title 2', 'test' || x'0a' || 'body 2', 2, '2018-01-01 00:00:00');

INSERT INTO file (uploader_id, post_id, file_name, file_contents)
VALUES
  (2, 2, 'test_file.pgn', 'b''[Event ""test event""]\n[Site ""test site""]\n[Date ""2023.10.17""]\n[Round ""4""]\n[White ""foo""]\n[Black ""bar""]\n[Result ""0-1""]\n\n1. e4 e5 2. d4 Nf6 3. Nc3 Nc6 4. d5 Nd4 5. Nf3 c5 6. Nxe5 Bd6 7. Bf4 O-O { test comment } 8. Nxf7 Rxf7 0-1\''');
