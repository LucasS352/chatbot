-- Seleciona o banco de dados 'pract'
USE pract;

-- Cria a tabela 'users' para armazenar informações dos usuários
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cria a tabela 'conversations' para armazenar o histórico de conversas
    CREATE TABLE `conversations` (
    `conversation_id` int(11) NOT NULL AUTO_INCREMENT,
    `client_id` int(11) NOT NULL,
    `start_time` timestamp NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (`conversation_id`),
    KEY `client_id` (`client_id`),
    CONSTRAINT `conversations_client_fk` FOREIGN KEY (`client_id`) REFERENCES `clients` (`client_id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;



-- Cria a tabela 'messages' para armazenar as mensagens individuais dentro das conversas
    CREATE TABLE `messages` (
    `message_id` int(11) NOT NULL AUTO_INCREMENT,
    `conversation_id` int(11) DEFAULT NULL,
    `sender` varchar(50) NOT NULL,
    `content` text NOT NULL,
    `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
    PRIMARY KEY (`message_id`),
    KEY `conversation_id` (`conversation_id`),
    CONSTRAINT `messages_conversation_fk` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`conversation_id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
    -- criando intençoes de perguntas e respostas. 
CREATE TABLE intents (
    intent_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,  -- Ex: "emitir nota fiscal"
    response TEXT NOT NULL        -- A resposta que o bot deve retornar
);
ALTER TABLE `intents` 
ADD COLUMN `quick_replies` TEXT NULL DEFAULT NULL AFTER `response`;

ALTER TABLE `intents` 
ADD COLUMN `images` TEXT NULL DEFAULT NULL AFTER `quick_replies`;

CREATE TABLE intent_variations (
    variation_id INT AUTO_INCREMENT PRIMARY KEY,
    intent_id INT,
    variation TEXT NOT NULL,
    FOREIGN KEY (intent_id) REFERENCES intents(intent_id) ON DELETE CASCADE
);

CREATE TABLE clients (
    client_id INT AUTO_INCREMENT PRIMARY KEY,
    client_name VARCHAR(255) UNIQUE NOT NULL,
    access_token VARCHAR(64) UNIQUE NOT NULL, -- Para armazenar a chave secreta
    master_api_token VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Adicionar um índice no token para buscas rápidas
CREATE INDEX idx_clients_access_token ON clients(access_token);


-- Antes de rodar isso, talvez você precise apagar os dados existentes ou fazer um backup
-- pois esta alteração quebra a estrutura antiga.
-- No phpMyAdmin, você pode fazer isso pela aba "Estrutura".
ALTER TABLE conversations
DROP FOREIGN KEY conversations_ibfk_1; -- O nome da chave pode variar

ALTER TABLE conversations
DROP COLUMN user_id,
ADD COLUMN client_id INT NOT NULL AFTER conversation_id,
ADD FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE;




#insersão de clientes 

INSERT INTO clients (client_name, access_token) 
VALUES ('magalu', 'a4ef17ab5b04447cc7f223b813fccef7bc52ab29e06b66a3');
