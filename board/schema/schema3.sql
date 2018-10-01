CREATE TABLE comment (idx int, comment varchar(50), constraint setidx foreign key(idx) references board(idx));
